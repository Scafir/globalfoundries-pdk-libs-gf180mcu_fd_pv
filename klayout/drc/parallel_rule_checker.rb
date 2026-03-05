require 'thread'
require 'stringio'
require 'io/wait'
require 'tmpdir'

# ============================================================================
# PARALLEL DRC RULE CHECKER - GF180 MCU PDK
# ============================================================================
#
# PURPOSE:
#   Executes KLayout DRC rule files in parallel using fork-based process model,
#   then merges results into single ReportDatabase.
#
# CRITICAL WARNING - GUI USAGE NOT SUPPORTED:
#   DO NOT use this class from within the KLayout GUI. Forking the GUI process
#   causes crashes due to shared file descriptors with Qt/Wayland. Requires
#   batch klayout execution (klayout -b or klayout -r).
#
# ARCHITECTURE:
#   Master process computes general layers, then forks N worker processes.
#   Workers execute individual rule files and write .lyrdb results.
#   Uses Copy-on-Write (CoW) memory sharing for efficiency - layout and
#   general layers remain in shared memory across all workers.
#
# USAGE EXAMPLE:
#   # Convert relative paths to absolute
#   rule_files = ["./rule_decks/comp.drc", "./rule_decks/cup.drc"]
#   rule_files = rule_files.map { |f| File.join(File.dirname(__FILE__), f) }
#
#   # Choose parallel or single-threaded execution
#   if thread_workers == 1
#     rule_files.each { |f| eval(File.read(f), binding, f) }
#   else
#     checker = ParallelRuleChecker.new(rule_files, binding, logger, num_workers: 8)
#     results = checker.run
#     results.save($report)
#   end
#
# PARAMETERS:
#   rule_files     : Array[String] - Absolute paths to .drc/.lyr rule files
#   rule_binding   : Binding - Ruby binding context (typically `binding` from script)
#   logger         : Object - Logger with .info(msg) method for status updates
#   num_workers    : Integer - Parallel workers (default: 4, total processes = N+1)
#
# TEMPORARY STORAGE:
#   Intermediate .lyrdb files stored in: tmpdir/drc_run_YYYY_MM_DD_HH_MM_S__/
#   Typical size: small (few MB). Auto-deleted on system reboot.
#
# BENEFITS vs. MULTIPLE KLAYOUT INSTANCES:
#   - Single layout/general-layer computation (no redundant work)
#   - CoW memory sharing (RAM usage similar to sequential, not multiplied)
#   - Single unified report (vs. needing post-processing of N separate reports)
#
# LIMITATIONS:
#   - Batch-mode only (not compatible with GUI)
#
# ============================================================================

class ParallelRuleChecker
  # Initializer for parallel DRC rule checking.
  #
  # Args:
  #   rule_files     : Array[String] - Absolute paths to .drc/.lyr rule files
  #   rule_binding   : Binding - Ruby binding context (typically `binding` from script)
  #   logger         : Object - Logger with .info(msg) method for status updates
  #   num_workers    : Integer - Number of parallel workers (default: 4)
  #
  # Creates a temporary directory for intermediate .lyrdb results.
  # Note: Results stored in timestamped temp dir
  def initialize(rule_files, rule_binding, logger, num_workers: 4)
    @rule_files = rule_files
    @rule_binding = rule_binding
    @logger = logger
    @num_workers = num_workers + 1 # +1 because master worker does no work
    timestamp = Time.now.strftime("drc_run_%Y_%m_%d_%H_%M_%S__")
    @tmpdir = Dir.mktmpdir(timestamp)
  end

  # Executes all DRC rules in parallel and returns aggregated results.
  #
  # Returns:
  #   RBA::ReportDatabase - Merged report containing all rule check results
  def run
    _run(@rule_files)
  end

  private
  # Merges two ReportDatabases, preserving db1's hierarchy structure.
  # Metadata from db2 is copied only if db1 is empty, allowing the first
  # database to serve as the "master" structure.
  #
  # Args:
  #   db1 : RBA::ReportDatabase - Database to merge into (preserved structure)
  #   db2 : RBA::ReportDatabase - Database to merge from
  #
  # Returns:
  #   RBA::ReportDatabase - Merged database with db1's structure intact
  #
  # PROCESS:
  #   Phase 1: Copy metadata (only if empty to preserve master values)
  #   Phase 2: Copy cell hierarchy and build mapping (RDB ID -> cell)
  #   Phase 3: Copy categories recursively, preserving full hierarchy
  #   Phase 4: Copy items (error counts, dimensions) mapping cells/categories
  def merge_databases(db1, db2)
    # === PHASE 1: COPY METADATA (only if db1 is empty) ===
    # Preserve db1's metadata; only copy from db2 if db1 lacks values
    if db1.description.empty? && !db2.description.empty?
      db1.description = db2.description
    end

    if db1.generator.empty? && !db2.generator.empty?
      db1.generator = db2.generator
    end

    if db1.top_cell_name.empty? && !db2.top_cell_name.empty?
      db1.top_cell_name = db2.top_cell_name
    end

    if db1.original_file.empty? && !db2.original_file.empty?
      db1.original_file = db2.original_file
    end

    # === PHASE 2: COPY CELL HIERARCHY ===
    # Each worker runs in separate process with its own database.
    # Build mapping of RDB IDs to allow linking items later.
    category_map = {}
    cell_map = {}

    db2.each_cell do |cell2|
      cell1 = db1.cell_by_qname(cell2.qname)
      if cell1.nil?
        cell1 = cell2.variant.empty? ?
          db1.create_cell(cell2.name) :
          db1.create_cell(cell2.name, cell2.variant)
      end
      cell_map[cell2.rdb_id] = cell1
    end

    # === PHASE 3: COPY CATEGORY TREE ===
    # Recursively traverse db2's category tree, creating matching structure in db1.
    # Uses RDB ID mapping and full paths ("top.level.sub") to preserve hierarchy.
    get_full_path = lambda do |cat|
      path_parts = []
      current = cat
      while current
        path_parts.unshift(current.name)
        current = current.parent
      end
      path_parts.join('.')
    end

    copy_category = lambda do |cat2, parent1|
      # Check if category already exists
      if parent1.nil?
        # Top-level category
        cat1 = db1.category_by_path(cat2.name)
        if cat1.nil?
          cat1 = db1.create_category(cat2.name)
        end
      else
        # Sub-category - check within parent
        parent_path = get_full_path.call(parent1)
        full_path = "#{parent_path}.#{cat2.name}"
        cat1 = db1.category_by_path(full_path)
        if cat1.nil?
          cat1 = db1.create_category(parent1, cat2.name)
        end
      end

      # Copy description from db2 if db1 is empty
      if cat1.description.empty? && !cat2.description.empty?
        cat1.description = cat2.description
      end

      # Store in map using RDB ID for later item linking
      full_path2 = get_full_path.call(cat2)
      category_map[cat2.rdb_id] = cat1

      # Recursively copy sub-categories
      cat2.each_sub_category do |sub_cat2|
        copy_category.call(sub_cat2, cat1)
      end
    end

    # Copy all top-level categories
    db2.each_category do |cat2|
      copy_category.call(cat2, nil)
    end

    # === PHASE 4: COPY ITEMS (ERRORS) ===
    # Transfer all error items from db2 to db1 using cell/category maps.
    # Copy all values (counts, dimensions) from each item.
    db2.each_item do |item2|
      cell1 = cell_map[item2.cell_id]
      cat1 = category_map[item2.category_id]

      if cell1 && cat1
        item1 = db1.create_item(cell1.rdb_id, cat1.rdb_id)

        # Copy all values from db2 item
        item2.each_value { |value| item1.add_value(value) }

        # Tags intentionally not copied (disabled functionality)
        # item2.each_tag { |tag_id| item1.add_tag(tag_id) }
      end
    end

    db1
  end

  # Executes all DRC rules in parallel using fork-based process model.
  #
  # IMPLEMENTATION DETAILS:
  #   - Master process forks N worker child processes.
  #   - Uses pipe-based IPC for task distribution and result collection.
  #   - Implements "ready"/"shutdown" handshake for flow control.
  #   - Aggregate results after all workers complete.
  #
  # PROCESS MODEL:
  #   Master spawns N workers + 1 (master does no work itself).
  #   Workers are fork'd children that execute rules in isolated processes.
  #   Uses Copy-on-Write (CoW) memory sharing - layout and general layers
  #   remain in shared memory across all workers.
  #
  # PIPE PROTOCOL:
  #   MASTER->WORKER: Master writes filename path to pipe
  #   WORKER->MASTER: Worker writes "ready" signals after completing tasks
  #   WORKER->MASTER: Each worker writes serialized results via separate pipe
  #   FLOW CONTROL: Master waits for "ready" before assigning new tasks
  def _run(rule_files)
    rule_files = @rule_files
    results = []

    # === PHASE 1: SPAWN WORKER PROCESSES ===
    # Creates @num_workers child proesses via fork().
    # Each puppet process:
    #   1. Closes unused pipe ends (clean fork, avoids descriptor leaks)
    #   2. Sends "ready" to indicate availability to master
    #   3. Enters loop: receives filename → executes rule → reports ready
    #
    # DATA STRUCTURES:
    #   puppets : Array of {:pid => int, :to_puppet => write_pipe, :from_puppet => read_pipe}
    #   pipes   : Array of [read_pipe, write_pipe] for result collection from each worker
    puppets = []
    pipes = @num_workers.times.map { IO.pipe }
    @num_workers.times do |i|
      reader, writer = pipes[i]
      master_to_puppet_r, master_to_puppet_w = IO.pipe
      puppet_to_master_r, puppet_to_master_w = IO.pipe

      pid = fork do
        reader.close  # Close unused pipe
        # Child (puppet) process starts here

        # Close all pipes in master->worker and worker->master direction
        # Only keep the ones needed for this worker's communication
        master_to_puppet_w.close
        puppet_to_master_r.close

        # Tell master we are ready (one-time handshake)
        puppet_to_master_w.puts "ready"
        puppet_to_master_w.flush

        # Execution loop: receive tasks until shutdown
        chunk_results = []
        loop do
          # Wait for next task (blocks until master writes something)
          task = master_to_puppet_r.gets
          if task == nil
            # EOF from master, exit gracefully
            sleep(0.01)
            next
          end
          task.chomp!

          # Exit condition from master
          break if task == "shutdown"

          @logger.info("Worker #{i}: Processing #{File.basename(task)}")
          begin
            result = execute_rule(task)
            chunk_results << result
          rescue => e
            # Broad rescue to capture any exception for user visibility
            @logger.info("Worker #{i}: Error processing #{File.basename(task)} : #{e.message}")
            chunk_results << { file: task, error: e.message }
          end
          @logger.info("Worker #{i}: Done processing #{File.basename(task)}")

          # Signal back to master that we're ready for next task
          puppet_to_master_w.puts "ready"
          puppet_to_master_w.flush

        end

        @logger.info("Worker #{i}: Shutting down")

        # Send accumulated results back to master via serialized pipe
        writer.write(Marshal.dump(chunk_results))
        writer.flush
        writer.close
        exit
      end

      # Master: close child-side of pipes we don't need
      writer.close
      master_to_puppet_r.close
      puppet_to_master_w.close

      puppets << {
        pid: pid,
        to_puppet: master_to_puppet_w,  # Write to this to send tasks
        from_puppet: puppet_to_master_r  # Read from this to get ready signals
      }
    end

    # === PHASE 2: TASK DISTRIBUTION (MASTER LOOP) ===
    # Master continuously monitors ready workers and assigns them files.
    # Uses non-blocking .ready?() checks on pipes for polling.
    #
    # CONTROL FLOW:
    #   1. Check which workers' pipes are ready (signal ready)
    #   2. If worker ready and work available: send task filename
    #   3. If worker ready and no work left: send shutdown command
    #   4. Repeat until all workers have shutdown
    strings_queue = rule_files.dup

    while !strings_queue.empty? || puppets.any?
      # Find workers that are ready (have signaled ready for new task)
      ready_pipes = puppets.map { |p| p[:from_puppet] }.select { |r| r.ready? }

      ready_pipes.each do |pipe|
        # Consume the "ready" signal
        pipe.gets

        # Find which worker this pipe belongs to
        puppet = puppets.find { |p| p[:from_puppet] == pipe }

        if strings_queue.empty?
          # No more tasks, signal worker to shut down
          puppet[:to_puppet].puts "shutdown"
          puppet[:to_puppet].flush
          # Remove from active worker list (will be cleaned up later)
          puppets.delete(puppet)
        else
          # Assign next task to idle worker
          next_string = strings_queue.shift
          puppet[:to_puppet].puts next_string
          puppet[:to_puppet].flush
        end
      end
    end

    # === PHASE 3: RESULT COLLECTION ===
    # After all workers complete and send shutdown, collect results.
    # Marshal serialization used for transferring complex Ruby objects
    # between processes.
    #
    # STEP:
    #   1. Read serialized results from each worker's result pipe
    #   2. Deserialize and collect into results array
    #   3. Wait for each child process to clean up OS resources
    pipes.each do |reader, _|
      # Deserialize results from this worker
      chunk_results = Marshal.load(reader.read)
      results.concat(chunk_results)
      reader.close
    end

    # Wait for all children to finish (OS process cleanup)
    puppets.each do |p|
      Process.wait(p[:pid])
    end

    @logger.info("All workers completed. Total results: #{results.size}")

    # === PHASE 4: AGGREGATE REPORTS ===
    # Merge all per-file ReportDatabases into single aggregated result.
    # Uses merge_databases to preserve hierarchy while combining error data.
    # Each .lyrdb from workers is loaded and merged sequentially.
    aggregated_res = RBA::ReportDatabase.new()
    results.each do |element|
      incoming_rep = RBA::ReportDatabase.new()
      incoming_rep.load(element[:result])
      aggregated_res = merge_databases(aggregated_res, incoming_rep)
    end

    aggregated_res
  end

  # Executes a single DRC rule file in the worker context.
  #
  # Process:
  #   1. Creates output path in temp dir: tmpdir/{filename}.lyrdb
  #   2. Initializes report object via KLayout binding
  #   3. Loads and evals rule code in KLayout binding context
  #   4. Saves report to .lyrdb file
  #
  # Args:
  #   file : String - Path to .drc/.lyr rule file
  #
  # Returns:
  #   Hash with keys:
  #     file      : basename of processed file
  #     result    : path to .lyrdb file OR error message if execution failed
  #     timestamp : Time when completion
  #
  # EXCEPTION HANDLING:
  #   All exceptions caught and stored in result hash, allowing worker
  #   to continue processing remaining files.
  def execute_rule(file)
    report_location = File.join(@tmpdir, "#{File.basename(file)}.lyrdb")
    @rule_binding.eval(%(r = report('Report for #{File.basename(file)}', '#{report_location}')))
    rule_code = File.read(file)
    eval(rule_code, @rule_binding, file)

    @rule_binding.local_variable_get(:r).rdb.save(report_location)
    {
      file: File.basename(file),
      result: report_location,
      timestamp: Time.now
    }
  rescue => e
    {
      file: File.basename(file),
      result: "ERROR: #{e.message}",
      timestamp: Time.now
    }
  end
end
