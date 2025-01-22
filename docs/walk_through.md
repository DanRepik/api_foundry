# Walkthrough: Creating an API with API Foundry

API Foundry is a powerful tool for deploying REST APIs integrated with relational databases on AWS. Unlike frameworks or ORM solutions, API Foundry focuses on automating the deployment of infrastructure to bridge your database with a fully managed REST API. It leverages the OpenAPI specification to define API behavior and integrates seamlessly with AWS services like Lambda and Secrets Manager.

By using API Foundry, you can minimize the complexities of API deployment while maintaining flexibility and security. It simplifies CRUD operations and allows for the execution of custom SQL queries defined directly in the OpenAPI specification. Sensitive database credentials are securely managed through AWS Secrets Manager, ensuring a robust and scalable deployment.

Two key components are required for an API Foundry deployment:

- **API Specification**: Use the OpenAPI specification to map database tables to component schema objects. API Foundry automatically generates CRUD services for these objects and supports defining custom SQL operations within the specification. Additionally, a tool is available to build a starting specification directly from an existing database, saving significant setup time.
- **Database Connection Secrets**: Secure sensitive database configuration using AWS Secrets Manager. These secrets must be set up beforehand and referenced during deployment to ensure secure access at runtime.

With API Foundry, developers can focus on designing their data models and API specifications while the tool handles the heavy lifting of infrastructure deployment and database interaction.

## Prerequisites

- **Python**: Ensure you have Python 3.8 or higher installed.

- **Pulumi**: Install Pulumi to manage infrastructure as code.

- **AWS CLI**: Configure AWS CLI with the necessary credentials.

- **Code Editor with Markdown Support**: To display line numbers in a code block within your Markdown documents, use a code editor or viewer that supports syntax highlighting and line numbering (e.g., Visual Studio Code or GitHub).

---

## Step-by-Step Process

### 1. Create a Pulumi Project

Begin by setting up a new Pulumi project using the AWS Python template:

```bash
pulumi new aws-python
```

Follow the prompts to configure your project. This will initialize a Pulumi project and create the necessary files to manage your infrastructure as code.

### 2. Install the API-Foundry Package

Start by activating your Python virtual environment for the project:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Next, install the API Foundry package by adding it to your `requirements.txt` file and installing dependencies:

```bash
echo "api-foundry" >> requirements.txt
pip install -r requirements.txt
```

To support a local development environment, you can also install the packages `localstack-playground` and `pulumi-local`. These require Docker to be installed, as they provision a Localstack container and associated databases.

### 3. Define the OpenAPI Specification

Use the OpenAPI format to define component schema objects corresponding to the database tables exposed by the API. Each database table must have a corresponding schema object. The properties of the schema map directly to the table columns. To simplify this process, API Foundry provides scripts that generate a starter specification by extracting schema information from the database.

For example:

```yaml
# filename: chinook_postgres.yaml
openapi: 3.1.0
info:
  title: Chinook RestAPI
  version: 1.0.0
components:
  schemas:
    album:
      type: object
      x-af-database: chinook-db
      properties:
        album_id:
          type: integer
          x-af-primary-key: auto
        title:
          type: string
          maxLength: 160
        artist_id:
          type: integer
        album_items:
          type: array
          items:
            $ref: '#/components/schemas/album'
          x-af-child-property: artist_id
          description: List of album items associated with this artist.
      required:
        - album_id
        - title
        - artist_id
    artist:
      type: object
      x-af-database: chinook-db
      properties:
        artist_id:
          type: integer
          x-af-primary-key: auto
        name:
          type: string
          maxLength: 120
        artist:
          $ref: '#/components/schemas/artist'
          x-af-parent-property: artist_id
          description: Artist associated with the album.
      required:
        - artist_id
```

In this example, only a couple of API Foundry's custom attributes (`x-af-database` and `x-af-primary-key`) have been used to define the schema. However, API Foundry supports additional attributes that allow for richer definitions of database resources, enabling more complex configurations and advanced capabilities.

### 4. Configure Database and Secure Access

Set up your database configuration and secure sensitive information in AWS Secrets Manager. For example:

- Store your database credentials, such as username, password, and connection string, in AWS Secrets Manager.
- Ensure appropriate IAM policies are configured to control access to the secrets.
- Verify the database is accessible and ready for API integration.

### 5. Run the Deployment Script

Deploy your API by running the main script:

```bash
python __main__.py
```

This script will:

- Create necessary AWS Lambda functions.
- Set up an API Gateway endpoint.
- Link the endpoint to the database using the OpenAPI configuration.

### 6. Test the API

Once deployed, test your API endpoints using tools like `curl` or Postman:

```bash
curl https://api.example.com/users
```

You should receive a JSON response based on your database records.

### 7. Customize for Advanced Needs

To handle specific requirements, you can define custom SQL operations in your OpenAPI paths. For instance:

```yaml
paths:
  /users/search:
    get:
      summary: Search users by name
      parameters:
        - name: name
          in: query
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'

