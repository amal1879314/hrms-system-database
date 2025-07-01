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
  marital_status VARCHAR(8) CHECK (marital_status IN ('married','unmarried')),
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


 INSERT INTO positions (position_id,title, description) VALUES
  (13,'HR Specialist', 'Handles HR duties'),
  (14,'Software Engineer', 'Develops software'),
  (15,'Sales Executive', 'Manages client accounts'),
  (16,'Financial Analyst', 'Oversees financial planning'),
  (17,'Marketing Manager', 'Leads marketing campaigns');

INSERT INTO employees (emp_id,employee_code, first_name, last_name, email, phone, dob, address, gender, marital_status, emergency_number, hire_date, dept_id, position_id, manager_id, role) VALUES
  (1,'E001','Alice','Johnson','alice.johnson@demo.com','+919876543210','1985-02-15','1st St, Kochi','female','married','+919876500001','2010-06-01', 5, 13, 1, 'HR_Manager'),
  (2,'E002','Bob','Smith','bob.smith@demo.com','+919876543211','1990-09-22','2nd St, Kochi','male','unmarried','+919876500002','2012-01-15', 6, 14, 1, 'Employee'),
  (3,'E003','Carol','Davis','carol.davis@demo.com','+919876543212','1988-12-05','3rd St, Kochi','female','married','+919876500003','2014-03-20', 7, 15, 1, 'Employee'),
  (4,'E004','David','Lee','david.lee@demo.com','+919876543213','1992-07-11','4th St, Kochi','male','unmarried','+919876500004','2016-11-10', 8, 16, 1, 'Employee'),
  (5,'E005','Eva','Williams','eva.williams@demo.com','+919876543214','1987-05-30','5th St, Kochi','female','unmarried','+919876500005','2018-08-25', 9, 17,1 , 'Employee');

INSERT INTO departments (dept_id,name) VALUES
  (5,'Human Resources'),
  (6,'Engineering'),
  (7,'Sales'),
  (8,'Finance'),
  (9,'Marketing');

INSERT INTO attendance (attendance_id,emp_id, date, clock_in, clock_out, status) VALUES
  (8,1,'2025-06-01','09:00','17:00','Present'),
  (9,2,'2025-06-01','09:15','17:10','Present'),
  (10,3,'2025-06-01',NULL,NULL,'Absent'),
  (11,4,'2025-06-01','09:05','13:00','Half Day'),
  (12,5,'2025-06-02','09:00','17:00','Present');


INSERT INTO leave_requests (leave_id,emp_id, leave_type, start_date, end_date, status, reviewed_by, reviewed_on) VALUES
  (22,1,'Annual Leave','2025-07-10','2025-07-15','Pending',NULL,NULL),
  (23,2,'Sick Leave','2025-06-20','2025-06-22','Approved',1,'2025-06-05 10:00'),
  (24,3,'Casual Leave','2025-07-01','2025-07-02','Rejected',1,'2025-06-10 14:30'),
  (25,4,'Annual Leave','2025-08-05','2025-08-10','Approved',1,'2025-06-12 16:20'),
  (26,5,'Sick Leave','2025-06-15','2025-06-16','Pending',NULL,NULL);



INSERT INTO payroll (payroll_id,emp_id, cycle_start, cycle_end, basic_salary, gross_salary, deductions, net_salary, status, created_by, created_on) VALUES
  (70,1,'2025-06-01','2025-06-30',50000.00,65000.00,5000.00,60000.00,'Draft',1,'2025-06-01 08:00'),
  (80,2,'2025-06-01','2025-06-30',45000.00,55000.00,4000.00,51000.00,'Approved',1,'2025-06-01 08:05'),
  (90,3,'2025-06-01','2025-06-30',40000.00,48000.00,3000.00,45000.00,'Paid',1,'2025-06-01 08:10'),
  (100,4,'2025-06-01','2025-06-30',42000.00,52000.00,3500.00,48500.00,'Draft',1,'2025-06-01 08:15'),
  (110,5,'2025-05-01','2025-05-31',50000.00,65000.00,5000.00,60000.00,'Paid',1,'2025-05-01 08:00');


INSERT INTO salary_structures (struct_id,position_id, basic, hra, da, allowances, deductions, effective_from, effective_to) VALUES
  (30,13,30000.00,10000.00,5000.00,'{"transport":2000,"medical":1500}','{"pf":1800,"tax":3000}','2025-01-01',NULL),
  (40,14,40000.00,12000.00,6000.00,'{"transport":2500,"medical":2000}','{"pf":2400,"tax":4000}','2025-01-01',NULL),
  (50,15,35000.00,11000.00,5500.00,'{"transport":2200,"medical":1800}','{"pf":2100,"tax":3500}','2025-01-01',NULL),
  (60,16,38000.00,11500.00,5700.00,'{"transport":2300,"medical":1900}','{"pf":2280,"tax":3800}','2025-01-01',NULL),
  (70,17,36000.00,11200.00,5600.00,'{"transport":2250,"medical":1850}','{"pf":2160,"tax":3600}','2025-01-01',NULL);

INSERT INTO job_postings (job_id,position_id, dept_id, posted_by, title, description, status, posted_on, closed_on) VALUES
  (200,13,5,1,'Software Engineer','Looking for mid‑level backend dev','Open','2025-06-01',NULL),
  (201,14,6,1,'Sales Executive','Experienced sales professional','Open','2025-05-15',NULL),
  (202,15,7,1,'Financial Analyst','Manage financial reporting','Closed','2025-04-01','2025-05-01'),
  (203,16,8,1,'Marketing Manager','Lead digital campaigns','Filled','2025-03-01','2025-04-15'),
  (204,17,9,1,'HR Specialist','Support HR operations','Open','2025-06-10',NULL);

INSERT INTO candidates (candidate_id,name, email, phone, resume_link, applied_on) VALUES
  (7,'Frank Miller','frank.miller@example.com','+919876543215','http://resume.example.com/fmiller.pdf','2025-06-05'),
  (8,'Grace Lee','grace.lee@example.com','+919876543216','http://resume.example.com/glee.pdf','2025-06-10'),
  (9,'Henry Kim','henry.kim@example.com','+919876543217','http://resume.example.com/hkim.pdf','2025-06-08'),
  (10,'Isla Zhang','isla.zhang@example.com','+919876543218','http://resume.example.com/izhang.pdf','2025-06-12'),
  (11,'Jack Brown','jack.brown@example.com','+919876543219','http://resume.example.com/jbrown.pdf','2025-06-07');

INSERT INTO applications (app_id,job_id, candidate_id, status, updated_on) VALUES
  (27,200,7,'Applied','2025-06-05 10:00'),
  (28,201,8,'Shortlisted','2025-06-12 11:30'),
  (29,202,9,'Applied','2025-06-08 09:45'),
  (30,203,10,'Interviewed','2025-06-15 14:00'),
  (31,204,11,'Rejected','2025-06-10 16:20');

INSERT INTO projects (project_id,name, description, start_date, end_date, status) VALUES
  (7,'Website Revamp','Redesign company website','2025-02-01','2025-08-31','Active'),
  (8,'Mobile App','Develop new mobile app','2025-03-15',NULL,'Planned'),
  (9,'CRM Integration','Integrate CRM system','2025-04-01','2025-07-15','On Hold'),
  (10,'Finance Audit','Quarterly audit','2025-05-01','2025-05-31','Completed'),
  (11,'Social Media Campaign','Boost engagement','2025-06-01',NULL,'Active');

  INSERT INTO employee_projects (emp_id, project_id, assigned_on, role, hours_allocated, is_active) VALUES
  (1,7,'2025-02-01','Backend Developer',160.00,TRUE),
  (2,8,'2025-02-05','Frontend Developer',150.00,TRUE),
  (3,9,'2025-04-01','Data Analyst',120.00,FALSE),
  (4,10,'2025-05-01','Auditor',80.00,FALSE),
  (5,11,'2025-06-01','App Developer',100.00,TRUE);













  
