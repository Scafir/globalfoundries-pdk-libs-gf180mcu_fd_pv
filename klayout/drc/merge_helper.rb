require 'thread'
require 'stringio'
require 'io/wait'
require 'tmpdir'
require 'yaml'
require 'pathname'

# Helper script to call merge_databases from Ruby
# Called via: klayout -b -r merge_helper.rb \
#     -rd input1=file1.lyrdb -rd input2=file2.lyrdb -rd output=result.lyrdb

# Load merge_databases from ParallelRuleChecker class
# Use File.expand_path to properly resolve path
SCRIPT_DIR = File.expand_path(File.dirname(__FILE__))
require File.join(SCRIPT_DIR, 'parallel_rule_checker.rb')

def merge_databases(db1, db2)
  checker = ParallelRuleChecker.new([], binding, nil, num_workers: 1)

  # Use send to call private method
  checker.send(:merge_databases, db1, db2)
end


if $input1.nil? || $input2.nil? || $output.nil?
  puts "Usage: klayout -r merge_helper.rb -rd input1=FILE -rd input2=FILE -rd output=FILE"
  exit 1
end

begin
  # Load input databases
  db1 = RBA::ReportDatabase.new
  db1.load($input1)

  db2 = RBA::ReportDatabase.new
  db2.load($input2)

  # Perform merge
  # Check if both databases have the same top cell name
  if db1.top_cell_name != db2.top_cell_name && !db1.top_cell_name.empty? && !db2.top_cell_name.empty?
    raise "Error: Cannot merge databases with different top cells: '#{db1.top_cell_name}' vs '#{db2.top_cell_name}'"
  end

  merged_db = merge_databases(db1, db2)

  # Save result
  merged_db.save($output)

  puts "Merge completed successfully: #{$output}"

rescue => e
  puts "ERROR: #{e.message}"
  puts e.backtrace.join("\n")
  exit 1
end
