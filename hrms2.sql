CREATE TABLE departments (
  dept_id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE positions (
  position_id SERIAL PRIMARY KEY,
  title VARCHAR(100) NOT NULL,
  description TEXT
);

CREATE TABLE employees (
  emp_id SERIAL PRIMARY KEY,
  employee_code VARCHAR(20) NOT NULL UNIQUE,
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  email VARCHAR(100) UNIQUE,
  phone VARCHAR(15),
  dob DATE,
  address VARCHAR(100) NOT NULL,
  gender VARCHAR(6) CHECK (gender IN ('male','female','other')),
  marital_status VARCHAR(8) CHECK (marital_status IN ('married','unmarried','devorced')),
  emergency_number VARCHAR(15),
  hire_date DATE,
  dept_id INT REFERENCES departments(dept_id),
  position_id INT REFERENCES positions(position_id),
  manager_id INT REFERENCES employees(emp_id),
  role VARCHAR(12) CHECK (role IN ('Admin','HR_Manager','Dept_Manager','Employee','Recruiter'))
);

CREATE TABLE attendance (
  attendance_id SERIAL PRIMARY KEY,
  emp_id INT NOT NULL REFERENCES employees(emp_id),
  date DATE NOT NULL,
  clock_in TIME,
  clock_out TIME,
  status VARCHAR(10) CHECK (status IN ('Present','Absent','Half Day','Leave','Holiday')),
  UNIQUE (emp_id, date)
);

CREATE TABLE leave_requests (
  leave_id SERIAL PRIMARY KEY,
  emp_id INT NOT NULL REFERENCES employees(emp_id),
  leave_type VARCHAR(50) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status VARCHAR(8) NOT NULL CHECK (status IN ('Pending','Approved','Rejected')),
  requested_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_by INT REFERENCES employees(emp_id),
  reviewed_on TIMESTAMP
);

CREATE TABLE payroll (
  payroll_id SERIAL PRIMARY KEY,
  emp_id INT NOT NULL REFERENCES employees(emp_id),
  cycle_start DATE NOT NULL,
  cycle_end DATE NOT NULL,
  basic_salary DECIMAL(12,2) NOT NULL,
  gross_salary DECIMAL(12,2) NOT NULL,
  deductions DECIMAL(12,2) NOT NULL,
  net_salary DECIMAL(12,2) NOT NULL,
  status VARCHAR(8) NOT NULL CHECK (status IN ('Draft','Approved','Paid')),
  created_by INT NOT NULL REFERENCES employees(emp_id),
  created_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE salary_structures (
  struct_id SERIAL PRIMARY KEY,
  position_id INT NOT NULL REFERENCES positions(position_id),
  basic DECIMAL(12,2),
  hra DECIMAL(12,2),
  da DECIMAL(12,2),
  allowances JSON,
  deductions JSON,
  effective_from DATE NOT NULL,
  effective_to DATE
);

CREATE TABLE job_postings (
  job_id SERIAL PRIMARY KEY,
  position_id INT NOT NULL REFERENCES positions(position_id),
  dept_id INT NOT NULL REFERENCES departments(dept_id),
  posted_by INT NOT NULL REFERENCES employees(emp_id),
  title VARCHAR(100) NOT NULL,
  description TEXT,
  status VARCHAR(6) NOT NULL CHECK (status IN ('Open','Closed','Filled')),
  posted_on DATE NOT NULL,
  closed_on DATE
);

CREATE TABLE candidates (
  candidate_id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100),
  phone VARCHAR(15),
  resume_link VARCHAR(255),
  applied_on DATE
);

CREATE TABLE applications (
  app_id SERIAL PRIMARY KEY,
  job_id INT NOT NULL REFERENCES job_postings(job_id),
  candidate_id INT NOT NULL REFERENCES candidates(candidate_id),
  status VARCHAR(12) NOT NULL CHECK (status IN ('Applied','Shortlisted','Interviewed','Hired','Rejected')),
  updated_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE projects (
  project_id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  description TEXT,
  start_date DATE,
  end_date DATE,
  status VARCHAR(10) NOT NULL DEFAULT 'Planned'
    CHECK (status IN ('Planned','Active','Completed','On Hold','Cancelled'))
);

CREATE TABLE employee_projects (
  emp_id INT NOT NULL REFERENCES employees(emp_id),
  project_id INT NOT NULL REFERENCES projects(project_id),
  assigned_on DATE NOT NULL DEFAULT CURRENT_DATE,
  role VARCHAR(100),
  hours_allocated DECIMAL(7,2),
  is_active BOOLEAN NOT NULL DEFAULT FALSE,
  updated_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (emp_id, project_id)
);








