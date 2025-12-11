import project_processing
import general_processing

print("Running project checker")
project_processing.run_checker()
print("Project checker complete.")
print()
print("Running general checker")
general_processing.process_content()
print("General processing complete.")
print("All pre-render jobs are complete, proceeding with render.")
print()
