The `api_foundry` project is a powerful tool designed to automate the deployment of REST APIs on AWS using Lambda services to access and interact with relational databases (RDBMS). This project leverages the OpenAPI specification to define and manage the APIs.

### Key Features:

- **AWS REST API Deployment**: `api_foundry` simplifies the deployment of RESTful APIs on AWS by integrating with AWS Lambda, allowing seamless interaction with various relational databases.

- **OpenAPI Specification**: The project uses the OpenAPI standard for defining API endpoints, request/response structures, and data schemas. This ensures that the APIs are well-documented, standardized, and easy to maintain.

- **Automatic Record Management**: When OpenAPI schema objects are linked to database tables, `api_foundry` automatically generates record management services. This includes the creation of standard CRUD (Create, Read, Update, Delete) operations, providing a robust and scalable solution for managing database records through the API.

- **Custom SQL Integration**: `api_foundry` allows developers to define custom SQL queries and associate them with specific OpenAPI path operations. This feature provides flexibility to perform complex queries and operations beyond standard CRUD functionalities, tailored to specific application requirements.

### Summary:

The `api_foundry` project streamlines the process of deploying APIs on AWS that interact with relational databases. By utilizing the OpenAPI specification, it not only ensures consistency and clarity in API design but also automates the creation of database-driven services and allows for custom SQL operations. This makes `api_foundry` an invaluable tool for developers looking to quickly deploy and manage data-centric APIs on the AWS platform.