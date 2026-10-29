# Human Resource Management System (HRMS)

A backend-focused Human Resource Management System developed using Python, FastAPI, and PostgreSQL to manage employee information and streamline core human resource operations through RESTful APIs.

## Overview

The HRMS provides a centralized system for managing employee records, departments, job positions, attendance, leave requests, payroll, projects, recruitment, and candidate applications.

The backend uses FastAPI to expose REST APIs and PostgreSQL to store relational data. Raw SQL queries are executed using psycopg2, while session-based authentication and password hashing support user authentication.

## Key Features

- **User Authentication:** User registration, login, logout, and password hashing.
- **Employee Management:** Create, retrieve, update, and delete employee records.
- **Department and Position Management:** Organize departments and job roles.
- **Attendance Tracking:** Maintain daily attendance records.
- **Leave Management:** Handle employee leave requests.
- **Payroll Management:** Manage payroll records and salary structures.
- **Project Management:** Assign employees to projects and track associations.
- **Recruitment Management:** Manage job postings, candidate information, and applications.
- **Relational Database Design:** Use PostgreSQL tables, foreign keys, and constraints to maintain data integrity.
- **RESTful API Communication:** Exchange structured data through JSON responses.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| FastAPI | REST API development |
| PostgreSQL | Relational database management |
| psycopg2 | PostgreSQL connectivity and raw SQL queries |
| Passlib | Password hashing |
| Session-based authentication | User login and session management |
| Flask and Jinja2 | Optional frontend rendering, if included in the implementation |
| HTML | User interface templates, if applicable |

## System Architecture

The system follows a backend-oriented architecture in which API endpoints handle requests, business logic processes operations, and PostgreSQL stores application data.

```text
Client / Frontend
       |
       v
   FastAPI Backend
       |
       v
  API and Business Logic
       |
       v
 psycopg2 + Raw SQL
       |
       v
    PostgreSQL
```

The API layer returns JSON responses and supports communication with a frontend application.

## Database Design

The database contains relational tables for the main HR operations:

| Table | Purpose |
|---|---|
| employees | Employee information |
| departments | Department records |
| positions | Job roles and designations |
| attendance | Daily attendance records |
| leave_requests | Employee leave applications |
| payroll | Payroll and salary records |
| salary_structures | Salary breakdowns by role |
| projects | Project information |
| employee_projects | Employee-to-project assignments |
| job_postings | Recruitment listings |
| candidates | Candidate information |
| applications | Job applications |

Foreign key relationships, constraints, and status fields help maintain relational integrity.

## API Endpoints

The following endpoints are documented for the project.

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/signup` | Register a user |
| POST | `/api/login` | Authenticate a user |
| POST | `/api/logout` | End a user session |

### Employee Management

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/employees` | List employees |
| GET | `/api/employees/{id}` | Retrieve an employee |
| PUT/PATCH | `/api/employees/{id}` | Update employee information |
| DELETE | `/api/employees/{id}` | Delete an employee |

### Departments and Positions

- `/api/departments` — Manage departments.
- `/api/positions` — Manage job roles and positions.

### Attendance

- `/api/attendance` — Add and retrieve attendance records.
- `/api/attendance/{id}` — Edit or delete an attendance record.

### Payroll

- `/api/payroll` — Generate or retrieve payroll records.
- `/api/payroll/{id}` — View or edit payroll information.

### Recruitment and Applications

- `/api/job_postings` — Create and manage job listings.
- `/api/applications` — Handle candidate applications.

### Project Assignments

- `/api/employee_projects` — Assign employees to projects.

Note: HTTP methods and individual operations should be verified against the actual route implementations in the source code.

## Authentication and Security

The project documents session-based authentication for managing user login sessions. Passlib is used for password hashing.

Database credentials and other secrets should be stored outside the source code. Authentication and authorization checks should be applied to protected endpoints as appropriate.

## Getting Started

### Prerequisites

- Python
- PostgreSQL
- pip
- Git

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/hrms-backend.git
cd hrms-backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

On macOS or Linux:

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

If the project contains a `requirements.txt` file:

```bash
pip install -r requirements.txt
```

Otherwise, install the dependencies specified by the project and create a requirements file after verifying the working environment.

### 4. Configure PostgreSQL

Create a PostgreSQL database and configure the database connection using environment variables or the configuration method already implemented in the project.

Do not commit database passwords, secret keys, or `.env` files to GitHub.

### 5. Run the application

Use the actual FastAPI application module and variable name from the source code. For example, if the entry point is `main.py` and the FastAPI instance is named `app`, run:

```bash
uvicorn main:app --reload
```

If the project uses a different module name or application structure, adjust the command accordingly.

When running locally, FastAPI's interactive API documentation is commonly available at:

`http://127.0.0.1:8000/docs`

## Challenges and Learning Outcomes

The project documentation identifies several backend engineering challenges:

- Integrating frontend rendering with a FastAPI backend in a hybrid architecture.
- Maintaining relational integrity while handling complex SQL joins.
- Managing session-based authentication alongside API communication.
- Designing normalized database tables that support future expansion.
- Organizing code to separate frontend and backend responsibilities.

This project provided practical experience with REST API development, PostgreSQL database design, raw SQL queries, authentication, and modular backend development.

## Future Enhancements

- Add automated unit and integration tests for API endpoints.
- Improve API authorization and input validation.
- Add structured logging and error handling.
- Introduce API pagination and filtering for large datasets.
- Add notifications and HR analytics.
- Extend the system with mobile application integration.
- Add automated deployment and CI/CD workflows.

## Author

**Amal Joe**

- GitHub: https://github.com/amal1879314
- LinkedIn: https://www.linkedin.com/in/amal-joe-93a485301

---

*This repository documents a Human Resource Management System backend project developed for learning and practical experience with Python, REST APIs, and relational databases.*

