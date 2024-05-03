import os
import shutil
from zipfile import ZipFile

# Define the Lambda function code
lambda_code = """
def lambda_handler(event, context):
    # Your Lambda function code here
    return 'Hello from Lambda!'
"""

# Write the Lambda function code to a file
with open('lambda_function.py', 'w') as f:
    f.write(lambda_code)

# Define the requirements
requirements = """
requests==2.26.0
pyyaml
psycopg2-binary
oracledb
"""

# Write the requirements to a file
with open('requirements.txt', 'w') as f:
    f.write(requirements)

# Install the requirements
os.system('pip install -r requirements.txt -t .')

# Create a ZIP archive of the Lambda function code and requirements
with ZipFile('lambda_function.zip', 'w') as zipf:
    zipf.write('lambda_function.py')
    zipf.write('requirements.txt')
    for folder_name, _, filenames in os.walk('requests'):
        for filename in filenames:
            file_path = os.path.join(folder_name, filename)
            zipf.write(file_path, os.path.relpath(file_path, '.'))

# Clean up
shutil.rmtree('requests')
os.remove('lambda_function.py')
os.remove('requirements.txt')

print("Lambda function archive created successfully!")
