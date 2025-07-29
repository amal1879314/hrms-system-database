from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from passlib.hash import bcrypt
from pydantic import BaseModel
import psycopg2
from config import config
from datetime import date , time ,datetime
from starlette.responses import RedirectResponse
from fastapi import status
from database import get_connection
from starlette.status import HTTP_302_FOUND
from pydantic import BaseModel , EmailStr
from typing import Optional
from psycopg2.extras import RealDictCursor
import traceback
from psycopg2.errors import ForeignKeyViolation
from pydantic import BaseModel, constr , conint
from typing import Dict
import json


api = APIRouter()

auth = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_connection():
    params = config()
    return psycopg2.connect(**params)

# -------------------------------
# Form-based (HTML) Endpoints
# -------------------------------

@auth.get("/login", response_class=HTMLResponse, name="auth.login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@auth.post("/login")
def login_user(request: Request, email: str = Form(...), password: str = Form(...), role: str = Form(...)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, password FROM users WHERE email = %s AND role = %s", (email, role))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and bcrypt.verify(password, user[1]):
        request.session["user"] = user[0]
        request.session["role"] = role
        return RedirectResponse(url="/profile", status_code=302)
    else:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Invalid email, password, or role"
        })

@auth.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@auth.post("/signup")
def signup_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...)
):
    conn = get_connection()
    cur = conn.cursor()
    try:
        hashed_pw = bcrypt.hash(password)
        cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                    (name, email, hashed_pw, role))
        conn.commit()
        return RedirectResponse(url="/login", status_code=302)
    except psycopg2.IntegrityError:
        conn.rollback()
        return templates.TemplateResponse("signup.html", {
            "request": request,
            "error": "Email already registered"
        })
    finally:
        cur.close()
        conn.close()

@auth.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    user = request.session.get("user")
    role = request.session.get("role")

    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM employees")
        total_employees = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM departments")
        total_departments = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
        active_projects = cur.fetchone()[0]

        from datetime import date
        today = date.today()

        cur.execute("SELECT COUNT(*) FROM attendance WHERE date = %s AND status = 'Present'", (today,))
        present_today = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM attendance WHERE date = %s AND status = 'Absent'", (today,))
        absent_today = cur.fetchone()[0]

        cur.close()
        conn.close()

    except Exception as e:
        print("DB Error:", e)
        total_employees = total_departments = active_projects = present_today = absent_today = "N/A"

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "role": role,
        "total_employees": total_employees,
        "total_departments": total_departments,
        "active_projects": active_projects,
        "present_today": present_today,
        "absent_today": absent_today
    })


@auth.get("/employees", response_class=HTMLResponse)
async def employees_page(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                e.emp_id,
                e.employee_code,
                e.first_name,
                e.last_name,
                e.email,
                e.phone,
                d.name AS department_name,
                p.title AS position_title,
                e.role
            FROM employees e
            LEFT JOIN departments d ON e.dept_id = d.dept_id
            LEFT JOIN positions p ON e.position_id = p.position_id
        """)

        rows = cur.fetchall()
        employees = [{
            'id': row[0],
            'code': row[1],
            'name': f"{row[2]} {row[3]}",
            'email': row[4],
            'phone': row[5],
            'department': row[6],
            'position': row[7],
            'role': row[8],
            'status': 'Active'
        } for row in rows]

        cur.close()
        conn.close()

    except Exception as e:
        print("Error loading employees:", e)
        employees = []

    return templates.TemplateResponse("employees.html", {"request": request, "employees": employees})

@auth.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@auth.get("/employee/add", response_class=HTMLResponse)
def get_add_employee(request: Request):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT dept_id, name FROM departments")
        departments = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]

        cur.execute("SELECT position_id, title FROM positions")
        positions = [{'id': row[0], 'title': row[1]} for row in cur.fetchall()]

        cur.execute("SELECT emp_id, first_name, last_name FROM employees")
        managers = [{'id': row[0], 'name': f"{row[1]} {row[2]}"} for row in cur.fetchall()]

        cur.close()
        conn.close()

        return templates.TemplateResponse("add_emp.html", {
            "request": request,
            "departments": departments,
            "positions": positions,
            "managers": managers
        })

    except Exception as e:
        print("Error loading form:", e)
        return HTMLResponse("Error while loading form", status_code=500)

@auth.get("/employee/{emp_id}/edit", response_class=HTMLResponse)
def get_edit_employee(request: Request, emp_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM employees WHERE emp_id = %s", (emp_id,))
        emp = cur.fetchone()

        if not emp:
            return HTMLResponse("Employee not found", status_code=404)

        cur.execute("SELECT dept_id, name FROM departments")
        departments = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]

        cur.execute("SELECT position_id, title FROM positions")
        positions = [{'id': row[0], 'title': row[1]} for row in cur.fetchall()]

        cur.execute("SELECT emp_id, first_name, last_name FROM employees WHERE emp_id != %s", (emp_id,))
        managers = [{'id': row[0], 'name': f"{row[1]} {row[2]}"} for row in cur.fetchall()]

        cur.close()
        conn.close()

        return templates.TemplateResponse("edit_emp.html", {
            "request": request,
            "emp": emp,
            "departments": departments,
            "positions": positions,
            "managers": managers
        })
    except Exception as e:
        print("Error in get_edit_employee:", e)
        return HTMLResponse("Error loading form", status_code=500)
@auth.post("/employee/{emp_id}/edit")
def post_edit_employee(
    emp_id: int,
    employee_code: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    dob: str = Form(...),
    address: str = Form(...),
    gender: str = Form(...),
    marital_status: str = Form(...),
    emergency_number: str = Form(...),
    hire_date: str = Form(...),
    dept_id: int = Form(...),
    position_id: int = Form(...),
    manager_id: str = Form(None),
    role: str = Form(...)
):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE employees SET
                employee_code = %s,
                first_name = %s,
                last_name = %s,
                email = %s,
                phone = %s,
                dob = %s,
                address = %s,
                gender = %s,
                marital_status = %s,
                emergency_number = %s,
                hire_date = %s,
                dept_id = %s,
                position_id = %s,
                manager_id = %s,
                role = %s
            WHERE emp_id = %s
        """, (
            employee_code, first_name, last_name, email, phone, dob, address,
            gender, marital_status, emergency_number, hire_date,
            dept_id, position_id, manager_id or None, role, emp_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        return RedirectResponse(url="/employees", status_code=302)
    except Exception as e:
        print("Error in post_edit_employee:", e)
        return HTMLResponse("Error updating employee", status_code=500)

@auth.get("/employee/{emp_id}", response_class=HTMLResponse)
async def view_employee_html(request: Request, emp_id: int):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                employee_code, first_name, last_name, email, phone,
                dob, address, gender, marital_status, emergency_number,
                hire_date,
                COALESCE((SELECT name FROM departments WHERE dept_id = e.dept_id), 'N/A'),
                COALESCE((SELECT title FROM positions WHERE position_id = e.position_id), 'N/A'),
                COALESCE((SELECT first_name || ' ' || last_name FROM employees WHERE emp_id = e.manager_id), 'N/A'),
                role
            FROM employees e
            WHERE emp_id = %s
        """, (emp_id,))
        emp = cur.fetchone()

        cur.close()
        conn.close()

        if not emp:
            return HTMLResponse(content="Employee not found", status_code=404)

        labels = [
            'Employee Code', 'First Name', 'Last Name', 'Email', 'Phone',
            'Date of Birth', 'Address', 'Gender', 'Marital Status', 'Emergency Number',
            'Hire Date', 'Department', 'Position', 'Manager', 'Role'
        ]
        emp_data = list(zip(labels, emp))

        return templates.TemplateResponse("view_emp.html", {"request": request, "emp_data": emp_data})

    except Exception as e:
        print("Error:", e)
        return HTMLResponse(content=f"Error loading employee: {e}", status_code=500)

@auth.get("/employee/{emp_id}/delete")
async def delete_employee_html(request: Request, emp_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM employees WHERE emp_id = %s", (emp_id,))
        conn.commit()
        cur.close()
        conn.close()    
    except Exception as e:
        print("Error deleting employee:", e)
        return RedirectResponse("/employees", status_code=302)

    return RedirectResponse("/employees", status_code=302)




@auth.get("/departments", response_class=HTMLResponse)
async def get_departments_html(request: Request):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT dept_id, name FROM departments ORDER BY dept_id")
        departments = cur.fetchall()
        cur.close()
        conn.close()

        # Convert the list of tuples to list of dicts (optional, if your template prefers dicts)
        departments_list = [{"dept_id": d[0], "name": d[1]} for d in departments]

        return templates.TemplateResponse("departments.html", {
            "request": request,
            "departments": departments_list
        })

    except Exception as e:
        print("Error fetching departments HTML:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch departments")




@auth.get("/departments/add", response_class=HTMLResponse, name="add_department")
async def show_add_department_form(request: Request):
    return templates.TemplateResponse("add_department.html", {"request": request})

@auth.post("/departments/add")
async def add_department_form(request: Request, name: str = Form(...)):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Check if department already exists
        cur.execute("SELECT 1 FROM departments WHERE name = %s", (name,))
        if cur.fetchone():
            return RedirectResponse(url="/departments?error=exists", status_code=status.HTTP_303_SEE_OTHER)

        # Insert new department
        cur.execute("INSERT INTO departments (name) VALUES (%s)", (name,))
        conn.commit()
        cur.close()
        conn.close()

        return RedirectResponse(url="/departments", status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        return RedirectResponse(url="/departments?error=server", status_code=status.HTTP_303_SEE_OTHER)


@auth.get("/departments/{dept_id}/edit", response_class=HTMLResponse, name="edit_department")
async def show_edit_department_form(request: Request, dept_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT name FROM departments WHERE dept_id = %s", (dept_id,))
        dept = cur.fetchone()
        cur.close()
        conn.close()

        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")

        return templates.TemplateResponse("edit_department.html", {
            "request": request,
            "dept_id": dept_id,
            "dept_name": dept[0]
        })

    except Exception as e:
        print("Error fetching department:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch department")

@auth.get("/departments/{dept_id}/delete", name="delete_department")
async def delete_department_html(dept_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM departments WHERE dept_id = %s", (dept_id,))
        conn.commit()
        cur.close()
        conn.close()

        return RedirectResponse(url="/departments", status_code=303)

    except Exception as e:
        print("Error deleting department:", e)
        raise HTTPException(status_code=500, detail="Failed to delete department")

@auth.post("/departments/{dept_id}/edit")
async def edit_department_html(dept_id: int, name: str = Form(...)):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE departments SET name = %s WHERE dept_id = %s", (name, dept_id))
        conn.commit()
        cur.close()
        conn.close()

        return RedirectResponse(url="/departments", status_code=303)

    except Exception as e:
        print("Error updating department:", e)
        raise HTTPException(status_code=500, detail="Failed to update department")


    
    
    
# -------------------------------
# JSON-based API Endpoints
# -------------------------------

class UserSignup(BaseModel):
    name: str
    email: str
    password: str
    role: str

class UserLogin(BaseModel):
    email: str
    password: str
    role: str

class DepartmentIn(BaseModel):
    name: str


class ProjectIn(BaseModel):
    name: str
    description: str
    start_date: str | None = None
    end_date: str | None = None
    status: str

class AttendanceIn(BaseModel):
    emp_id: int
    date: date
    clock_in: time | None = None
    clock_out: time | None = None
    status: str  # Should be: Present, Absent, Half Day, Leave, Holiday

attendance = APIRouter()

class AttendanceBase(BaseModel):
    emp_id: int
    date: date
    clock_in: Optional[time] = None
    clock_out: Optional[time] = None
    status: str
  
class LeaveRequestBase(BaseModel):
    emp_id: int
    leave_type: str
    start_date: date
    end_date: date
    status: str  # 'Pending', 'Approved', or 'Rejected'
    reviewed_by: Optional[int] = None
    reviewed_on: Optional[datetime] = None  

class PayrollBase(BaseModel):
    emp_id: int
    cycle_start: date
    cycle_end: date
    basic_salary: float
    gross_salary: float
    deductions: float
    net_salary: float
    status: str
    created_by: int
    
class JobPostingBase(BaseModel):
    position_id: int
    dept_id: int
    posted_by: int
    title: str
    description: Optional[str] = None
    status: str  # Open, Closed, Filled
    posted_on: date
    closed_on: Optional[date] = None
    
@auth.post("/api/signup")
def api_signup(user: UserSignup):
    conn = get_connection()
    cur = conn.cursor()
    try:
        hashed_pw = bcrypt.hash(user.password)
        cur.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                    (user.name, user.email, hashed_pw, user.role))
        conn.commit()
        return {"message": "Signup successful"}
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    finally:
        cur.close()
        conn.close()

@auth.post("/api/login")
def api_login(user: UserLogin, request: Request):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, password FROM users WHERE email = %s AND role = %s", (user.email, user.role))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row and bcrypt.verify(user.password, row[1]):
        request.session["user"] = row[0]
        request.session["role"] = user.role
        return {"message": "Login successful", "user": row[0], "role": user.role}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@auth.get("/api/profile")
def api_profile(request: Request):
    user = request.session.get("user")
    role = request.session.get("role")

    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM employees")
        total_employees = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM departments")
        total_departments = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM projects WHERE status = 'Active'")
        active_projects = cur.fetchone()[0]

        from datetime import date
        today = date.today()

        cur.execute("SELECT COUNT(*) FROM attendance WHERE date = %s AND status = 'Present'", (today,))
        present_today = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM attendance WHERE date = %s AND status = 'Absent'", (today,))
        absent_today = cur.fetchone()[0]

        cur.close()
        conn.close()

        return {
            "user": user,
            "role": role,
            "total_employees": total_employees,
            "total_departments": total_departments,
            "active_projects": active_projects,
            "present_today": present_today,
            "absent_today": absent_today
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/api/employees")
async def get_employees_json():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                e.emp_id,
                e.employee_code,
                e.first_name,
                e.last_name,
                e.email,
                e.phone,
                d.name AS department_name,
                p.title AS position_title,
                e.role
            FROM employees e
            LEFT JOIN departments d ON e.dept_id = d.dept_id
            LEFT JOIN positions p ON e.position_id = p.position_id
        """)

        rows = cur.fetchall()
        employees = []
        for row in rows:
            employees.append({
                'id': row[0],
                'code': row[1],
                'name': f"{row[2]} {row[3]}",
                'email': row[4],
                'phone': row[5],
                'department': row[6],
                'position': row[7],
                'role': row[8],
                'status': "Active"
            })

        cur.close()
        conn.close()

    except Exception as e:
        print("Error loading employees:", e)
        employees = []

    return {"employees": employees}


@auth.post("/api/logout")
def api_logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}

from pydantic import BaseModel
from fastapi import HTTPException, Request
from datetime import date

# Step 1: Define the expected JSON input
class EmployeeCreate(BaseModel):
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str
    dob: date
    address: str
    gender: str
    marital_status: str
    emergency_number: str
    hire_date: date
    dept_id: int
    position_id: int
    manager_id: int | None = None
    role: str

# Step 2: Add the endpoint
@auth.post("/api/employee/add")
def add_employee_api(employee: EmployeeCreate):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO employees (
                employee_code, first_name, last_name, email, phone, dob, address,
                gender, marital_status, emergency_number, hire_date, dept_id,
                position_id, manager_id, role
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            employee.employee_code,
            employee.first_name,
            employee.last_name,
            employee.email,
            employee.phone,
            employee.dob,
            employee.address,
            employee.gender,
            employee.marital_status,
            employee.emergency_number,
            employee.hire_date,
            employee.dept_id,
            employee.position_id,
            employee.manager_id,
            employee.role
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Employee added successfully"}

    except Exception as e:
        print("Error adding employee:", e)
        raise HTTPException(status_code=500, detail=str(e))


class EmployeeCreate(BaseModel):
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str
    dob: date
    address: str
    gender: str
    marital_status: str
    emergency_number: str
    hire_date: date
    dept_id: int
    position_id: int
    manager_id: Optional[int] = None
    role: str


class EmployeeUpdate(BaseModel):
    employee_code: str
    first_name: str
    last_name: str
    email: str
    phone: str
    dob: date
    address: str
    gender: str
    marital_status: str
    emergency_number: str
    hire_date: date
    dept_id: int
    position_id: int
    manager_id: Optional[int]
    role: str

@api.get("/api/employee/{emp_id}")
def get_employee_data(emp_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Fetch employee record
        cur.execute("SELECT * FROM employees WHERE emp_id = %s", (emp_id,))
        emp = cur.fetchone()
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")

        # Fetch dropdown values
        cur.execute("SELECT dept_id, name FROM departments")
        departments = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]

        cur.execute("SELECT position_id, title FROM positions")
        positions = [{'id': row[0], 'title': row[1]} for row in cur.fetchall()]

        cur.execute("SELECT emp_id, first_name, last_name FROM employees WHERE emp_id != %s", (emp_id,))
        managers = [{'id': row[0], 'name': f"{row[1]} {row[2]}"} for row in cur.fetchall()]

        cur.close()
        conn.close()

        return JSONResponse(content={
            "employee": dict(emp),
            "departments": departments,
            "positions": positions,
            "managers": managers
        })

    except Exception as e:
        print("Error fetching employee:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@auth.put("/api/employee/{emp_id}")
def update_employee_json(emp_id: int, payload: EmployeeUpdate):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            UPDATE employees SET
                employee_code = %s,
                first_name = %s,
                last_name = %s,
                email = %s,
                phone = %s,
                dob = %s,
                address = %s,
                gender = %s,
                marital_status = %s,
                emergency_number = %s,
                hire_date = %s,
                dept_id = %s,
                position_id = %s,
                manager_id = %s,
                role = %s
            WHERE emp_id = %s
        """, (
            payload.employee_code, payload.first_name, payload.last_name, payload.email,
            payload.phone, payload.dob, payload.address, payload.gender,
            payload.marital_status, payload.emergency_number, payload.hire_date,
            payload.dept_id, payload.position_id, payload.manager_id,
            payload.role, emp_id
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Employee updated successfully"}

    except Exception as e:
        # ✅ Now returns actual error in Postman
        raise HTTPException(status_code=500, detail=str(e))


@auth.get("/api/employee/{emp_id}")
async def view_employee_json(emp_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                employee_code, first_name, last_name, email, phone,
                dob, address, gender, marital_status, emergency_number,
                hire_date,
                COALESCE((SELECT name FROM departments WHERE dept_id = e.dept_id), 'N/A'),
                COALESCE((SELECT title FROM positions WHERE position_id = e.position_id), 'N/A'),
                COALESCE((SELECT first_name || ' ' || last_name FROM employees WHERE emp_id = e.manager_id), 'N/A'),
                role
            FROM employees e
            WHERE emp_id = %s
        """, (emp_id,))
        emp = cur.fetchone()

        cur.close()
        conn.close()

        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")

        keys = [
            'employee_code', 'first_name', 'last_name', 'email', 'phone',
            'dob', 'address', 'gender', 'marital_status', 'emergency_number',
            'hire_date', 'department', 'position', 'manager', 'role'
        ]
        return dict(zip(keys, emp))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

from fastapi import HTTPException

@auth.delete("/api/employee/{emp_id}")
async def delete_employee_json(emp_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Check if employee exists
        cur.execute("SELECT * FROM employees WHERE emp_id = %s", (emp_id,))
        if not cur.fetchone():
            return JSONResponse(content={"error": "Employee not found"}, status_code=404)

        fallback_emp_id = 2  # ✅ Update to a valid existing employee ID (e.g., admin)

        # 1. Nullify or reassign references
        cur.execute("UPDATE employees SET manager_id = NULL WHERE manager_id = %s", (emp_id,))
        cur.execute("UPDATE leave_requests SET reviewed_by = NULL WHERE reviewed_by = %s", (emp_id,))
        cur.execute("UPDATE job_postings SET posted_by = %s WHERE posted_by = %s", (fallback_emp_id, emp_id))
        cur.execute("UPDATE payroll SET created_by = %s WHERE created_by = %s", (fallback_emp_id, emp_id))

        # 2. Delete direct dependencies
        cur.execute("DELETE FROM attendance WHERE emp_id = %s", (emp_id,))
        cur.execute("DELETE FROM leave_requests WHERE emp_id = %s", (emp_id,))
        cur.execute("DELETE FROM payroll WHERE emp_id = %s", (emp_id,))
        cur.execute("DELETE FROM employee_projects WHERE emp_id = %s", (emp_id,))  # ✅ New line

        # 3. Delete the employee
        cur.execute("DELETE FROM employees WHERE emp_id = %s", (emp_id,))
        conn.commit()

        cur.close()
        conn.close()

        return JSONResponse(content={"message": "Employee deleted successfully"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": f"Failed to delete employee: {str(e)}"}, status_code=500)


@auth.get("/departments/json", response_class=JSONResponse)
async def get_departments_json():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT dept_id, name FROM departments ORDER BY dept_id")
        departments = cur.fetchall()
        cur.close()
        conn.close()
        return {"departments": departments}
    except Exception as e:
        print("Error fetching departments JSON:", e)
        raise HTTPException(status_code=500, detail="Failed to fetch departments")

@auth.post("/departments/add/json", response_class=JSONResponse)
async def add_department_json(dept: DepartmentIn):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Check if department already exists
        cur.execute("SELECT 1 FROM departments WHERE name = %s", (dept.name,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Department already exists")

        # Insert new department
        cur.execute("INSERT INTO departments (name) VALUES (%s)", (dept.name,))
        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Department added successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add department: {str(e)}")



@auth.put("/departments/{dept_id}/edit/json", response_class=JSONResponse)
async def edit_department_json(dept_id: int, name: str = Form(...)):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE departments SET name = %s WHERE dept_id = %s", (name, dept_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Department updated successfully"}
    except Exception as e:
        print("Error updating department:", e)
        raise HTTPException(status_code=500, detail="Failed to update department")


@auth.delete("/departments/{dept_id}/delete/json", response_class=JSONResponse)
async def delete_department_json(dept_id: int):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM departments WHERE dept_id = %s", (dept_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Department not found")

        cur.execute("DELETE FROM departments WHERE dept_id = %s", (dept_id,))
        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Department deleted successfully"}

    except ForeignKeyViolation:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete department because it has employees assigned."
        )
    except Exception as e:
        traceback_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        raise HTTPException(status_code=500, detail=f"Failed to delete department: {str(e)}\n{traceback_str}")


@auth.get("/projects/json", response_class=JSONResponse)
async def get_projects_json():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT project_id, name, description, start_date, end_date, status FROM projects")
        rows = cur.fetchall()

        projects = []
        for row in rows:
            projects.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'start_date': row[3],
                'end_date': row[4],
                'status': row[5]
            })

        cur.close()
        conn.close()

        return {"projects": projects}

    except Exception as e:
        print("Error loading projects:", e)
        raise HTTPException(status_code=500, detail="Failed to load projects")


@auth.post("/projects/add/json", response_class=JSONResponse)
async def add_project_json(project: ProjectIn):
    try:
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO projects (name, description, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING project_id
        """, (project.name, project.description, project.start_date, project.end_date, project.status))

        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return {
            "message": "Project added successfully",
            "project_id": new_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add project: {str(e)}")


@auth.get("/projects/{project_id}/json", response_class=JSONResponse)
async def view_project_json(project_id: int):
    try:
        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()

        cur.execute("""
            SELECT project_id, name, description, start_date, end_date, status
            FROM projects WHERE project_id = %s
        """, (project_id,))
        row = cur.fetchone()

        cur.close()
        conn.close()

        if row:
            project = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "start_date": str(row[3]),
                "end_date": str(row[4]),
                "status": row[5]
            }
            return project
        else:
            raise HTTPException(status_code=404, detail="Project not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error viewing project: {str(e)}")


@auth.put("/projects/{project_id}/edit/json", response_class=JSONResponse)
async def edit_project_json(project_id: int, request: Request):
    data = await request.json()

    name = data.get("name")
    description = data.get("description")
    start_date = data.get("start_date")  # optional
    end_date = data.get("end_date")      # optional
    status = data.get("status")

    if not name or not description or not status:
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            UPDATE projects 
            SET name = %s, description = %s, start_date = %s, end_date = %s, status = %s 
            WHERE project_id = %s
        """, (name, description, start_date, end_date, status, project_id))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Project updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@auth.delete("/projects/{project_id}/delete/json", response_class=JSONResponse)
async def delete_project_json(project_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))
        conn.commit()

        cur.close()
        conn.close()

        return {"message": "Project deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting project: {str(e)}")

@auth.post("/attendance/add/json", response_class=JSONResponse)
async def add_attendance(attendance: AttendanceIn):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO attendance (emp_id, date, clock_in, clock_out, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            attendance.emp_id,
            attendance.date,
            attendance.clock_in,
            attendance.clock_out,
            attendance.status
        ))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Attendance record added successfully."}

    except psycopg2.errors.UniqueViolation:
        raise HTTPException(status_code=400, detail="Attendance for this employee on this date already exists.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add attendance: {str(e)}")

@auth.post("/attendance/create/json")
def create_attendance(data: AttendanceBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        # Check for existing attendance
        cur.execute("SELECT 1 FROM attendance WHERE emp_id = %s AND date = %s", (data.emp_id, data.date))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Attendance already exists")

        cur.execute("""
            INSERT INTO attendance (emp_id, date, clock_in, clock_out, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.emp_id, data.date, data.clock_in, data.clock_out, data.status))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Attendance created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth.get("/attendance/all/json")
def get_all_attendance():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("SELECT * FROM attendance ORDER BY date DESC")
        rows = cur.fetchall()
        result = []

        for row in rows:
            result.append({
                "attendance_id": row[0],
                "emp_id": row[1],
                "date": row[2],
                "clock_in": str(row[3]) if row[3] else None,
                "clock_out": str(row[4]) if row[4] else None,
                "status": row[5]
            })

        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/attendance/employee/{emp_id}/json")
def get_attendance_by_employee(emp_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("SELECT * FROM attendance WHERE emp_id = %s", (emp_id,))
        rows = cur.fetchall()
        result = []

        for row in rows:
            result.append({
                "attendance_id": row[0],
                "emp_id": row[1],
                "date": row[2],
                "clock_in": str(row[3]) if row[3] else None,
                "clock_out": str(row[4]) if row[4] else None,
                "status": row[5]
            })

        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.put("/attendance/update/{attendance_id}/json")
def update_attendance(attendance_id: int, data: AttendanceBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            UPDATE attendance 
            SET emp_id = %s, date = %s, clock_in = %s, clock_out = %s, status = %s
            WHERE attendance_id = %s
        """, (data.emp_id, data.date, data.clock_in, data.clock_out, data.status, attendance_id))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Attendance updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/attendance/delete/{attendance_id}/json")
def delete_attendance(attendance_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("DELETE FROM attendance WHERE attendance_id = %s", (attendance_id,))
        conn.commit()

        cur.close()
        conn.close()
        return {"message": "Attendance deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@auth.post("/leave/create/json")
def create_leave(data: LeaveRequestBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO leave_requests (emp_id, leave_type, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.emp_id, data.leave_type, data.start_date, data.end_date, data.status))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Leave request created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/leave/all/json")
def get_all_leave_requests():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("SELECT * FROM leave_requests ORDER BY requested_on DESC")
        rows = cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "leave_id": row[0],
                "emp_id": row[1],
                "leave_type": row[2],
                "start_date": row[3],
                "end_date": row[4],
                "status": row[5],
                "requested_on": row[6],
                "reviewed_by": row[7],
                "reviewed_on": row[8]
            })

        cur.close()
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/leave/employee/{emp_id}/json")
def get_leave_by_employee(emp_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("SELECT * FROM leave_requests WHERE emp_id = %s ORDER BY requested_on DESC", (emp_id,))
        rows = cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "leave_id": row[0],
                "emp_id": row[1],
                "leave_type": row[2],
                "start_date": row[3],
                "end_date": row[4],
                "status": row[5],
                "requested_on": row[6],
                "reviewed_by": row[7],
                "reviewed_on": row[8]
            })

        cur.close()
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.put("/leave/approve/{leave_id}/json")
def approve_leave(leave_id: int, reviewer_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            UPDATE leave_requests 
            SET status = 'Approved', reviewed_by = %s, reviewed_on = CURRENT_TIMESTAMP
            WHERE leave_id = %s
        """, (reviewer_id, leave_id))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Leave request approved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.put("/leave/reject/{leave_id}/json")
def reject_leave(leave_id: int, reviewer_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            UPDATE leave_requests 
            SET status = 'Rejected', reviewed_by = %s, reviewed_on = CURRENT_TIMESTAMP
            WHERE leave_id = %s
        """, (reviewer_id, leave_id))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Leave request rejected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/leave/delete/{leave_id}/json")
def delete_leave(leave_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("DELETE FROM leave_requests WHERE leave_id = %s", (leave_id,))
        conn.commit()

        cur.close()
        conn.close()
        return {"message": "Leave request deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth .post("/payroll/add/json")
def add_payroll(data: PayrollBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO payroll (emp_id, cycle_start, cycle_end, basic_salary, gross_salary, deductions, net_salary, status, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.emp_id, data.cycle_start, data.cycle_end, data.basic_salary,
            data.gross_salary, data.deductions, data.net_salary,
            data.status, data.created_by
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Payroll record added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/payroll/all/json")
def get_all_payroll():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM payroll ORDER BY created_on DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "payroll_id": row[0],
                "emp_id": row[1],
                "cycle_start": row[2],
                "cycle_end": row[3],
                "basic_salary": float(row[4]),
                "gross_salary": float(row[5]),
                "deductions": float(row[6]),
                "net_salary": float(row[7]),
                "status": row[8],
                "created_by": row[9],
                "created_on": row[10]
            })
        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/payroll/employee/{emp_id}/json")
def get_payroll_by_employee(emp_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM payroll WHERE emp_id = %s ORDER BY created_on DESC", (emp_id,))
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "payroll_id": row[0],
                "emp_id": row[1],
                "cycle_start": row[2],
                "cycle_end": row[3],
                "basic_salary": float(row[4]),
                "gross_salary": float(row[5]),
                "deductions": float(row[6]),
                "net_salary": float(row[7]),
                "status": row[8],
                "created_by": row[9],
                "created_on": row[10]
            })
        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.put("/payroll/update/{payroll_id}/json")
def update_payroll(payroll_id: int, data: PayrollBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            UPDATE payroll 
            SET emp_id=%s, cycle_start=%s, cycle_end=%s, basic_salary=%s,
                gross_salary=%s, deductions=%s, net_salary=%s,
                status=%s, created_by=%s
            WHERE payroll_id=%s
        """, (
            data.emp_id, data.cycle_start, data.cycle_end, data.basic_salary,
            data.gross_salary, data.deductions, data.net_salary,
            data.status, data.created_by, payroll_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Payroll record updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/payroll/delete/{payroll_id}/json")
def delete_payroll(payroll_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("DELETE FROM payroll WHERE payroll_id = %s", (payroll_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Payroll record deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.post("/job-postings/add/json")
def add_job_posting(data: JobPostingBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO job_postings (position_id, dept_id, posted_by, title, description, status, posted_on, closed_on)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.position_id, data.dept_id, data.posted_by, data.title, data.description,
            data.status, data.posted_on, data.closed_on
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Job posting created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/job-postings/all/json")
def get_all_job_postings():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM job_postings ORDER BY posted_on DESC")
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "job_id": row[0],
                "position_id": row[1],
                "dept_id": row[2],
                "posted_by": row[3],
                "title": row[4],
                "description": row[5],
                "status": row[6],
                "posted_on": row[7],
                "closed_on": row[8]
            })
        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/job-postings/by-department/{dept_id}/json")
def get_job_postings_by_department(dept_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM job_postings WHERE dept_id = %s", (dept_id,))
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "job_id": row[0],
                "position_id": row[1],
                "dept_id": row[2],
                "posted_by": row[3],
                "title": row[4],
                "description": row[5],
                "status": row[6],
                "posted_on": row[7],
                "closed_on": row[8]
            })
        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@auth.put("/job-postings/update/{job_id}/json")
def update_job_posting(job_id: int, data: JobPostingBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            UPDATE job_postings 
            SET position_id=%s, dept_id=%s, posted_by=%s, title=%s, description=%s,
                status=%s, posted_on=%s, closed_on=%s
            WHERE job_id=%s
        """, (
            data.position_id, data.dept_id, data.posted_by, data.title, data.description,
            data.status, data.posted_on, data.closed_on, job_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Job posting updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/job-postings/delete/{job_id}/json")
def delete_job_posting(job_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("DELETE FROM job_postings WHERE job_id = %s", (job_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Job posting deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EmployeeProjectBase(BaseModel):
    emp_id: int
    project_id: int
    assigned_on: date
    role: str
    hours_allocated: float
    is_active: bool
    updated_on: datetime

@auth.post("/employee-projects/add/json")
def add_employee_project(data: EmployeeProjectBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO employee_projects (emp_id, project_id, assigned_on, role, hours_allocated, is_active, updated_on)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data.emp_id, data.project_id, data.assigned_on, data.role,
            data.hours_allocated, data.is_active, data.updated_on
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Employee assigned to project successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/employee-projects/all/json")
def get_all_employee_projects():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM employee_projects")
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "emp_id": row[0],
                "project_id": row[1],
                "assigned_on": row[2],
                "role": row[3],
                "hours_allocated": row[4],
                "is_active": row[5],
                "updated_on": row[6]
            })
        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/employee-projects/by-employee/{emp_id}/json")
def get_projects_by_employee(emp_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM employee_projects WHERE emp_id = %s", (emp_id,))
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "emp_id": row[0],
                "project_id": row[1],
                "assigned_on": row[2],
                "role": row[3],
                "hours_allocated": row[4],
                "is_active": row[5],
                "updated_on": row[6]
            })
        cur.close()
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class EmployeeProjectUpdate(BaseModel):
    assigned_on: date
    role: str
    hours_allocated: float
    is_active: bool
    updated_on: datetime

@auth.put("/employee-projects/update/{emp_id}/{project_id}/json")
def update_employee_project(emp_id: int, project_id: int, data: EmployeeProjectUpdate):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            UPDATE employee_projects
            SET assigned_on=%s, role=%s, hours_allocated=%s, is_active=%s, updated_on=%s
            WHERE emp_id=%s AND project_id=%s
        """, (
            data.assigned_on, data.role, data.hours_allocated,
            data.is_active, data.updated_on, emp_id, project_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Assignment updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/employee-projects/delete/{emp_id}/{project_id}/json")
def delete_employee_project(emp_id: int, project_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("DELETE FROM employee_projects WHERE emp_id = %s AND project_id = %s", (emp_id, project_id))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Assignment deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PositionBase(BaseModel):
    title: str
    description: str | None = None

@auth.post("/positions/add/json")
def add_position(data: PositionBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("INSERT INTO positions (title, description) VALUES (%s, %s)",
                    (data.title, data.description))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Position added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/positions/all/json")
def get_all_positions():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM positions ORDER BY position_id")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {"position_id": r[0], "title": r[1], "description": r[2]}
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/positions/{position_id}/json")
def get_position_by_id(position_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("SELECT * FROM positions WHERE position_id = %s", (position_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return {"position_id": row[0], "title": row[1], "description": row[2]}
        else:
            raise HTTPException(status_code=404, detail="Position not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.put("/positions/update/{position_id}/json")
def update_position(position_id: int, data: PositionBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("UPDATE positions SET title = %s, description = %s WHERE position_id = %s",
                    (data.title, data.description, position_id))

        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Position updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/positions/delete/{position_id}/json")
def delete_position(position_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("DELETE FROM positions WHERE position_id = %s", (position_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Position deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SalaryStructureBase(BaseModel):
    position_id: int
    basic: Optional[float] = 0.0
    hra: Optional[float] = 0.0
    da: Optional[float] = 0.0
    allowances: Optional[Dict[str, float]] = {}
    deductions: Optional[Dict[str, float]] = {}
    effective_from: date
    effective_to: Optional[date] = None

@auth.post("/salary-structure/add/json")
def add_salary_structure(data: SalaryStructureBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO salary_structures 
            (position_id, basic, hra, da, allowances, deductions, effective_from, effective_to)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.position_id, data.basic, data.hra, data.da,
            json.dumps(data.allowances), json.dumps(data.deductions),
            data.effective_from, data.effective_to
        ))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Salary structure added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CandidateBase(BaseModel):
    name: str
    email: str
    phone: str
    resume_link: str
    applied_on: date

class CandidateUpdate(CandidateBase):
    name: str
    email: str
    phone: str
    resume_link: str
    applied_on: date

class CandidateOut(CandidateBase):
    name: str
    email: str
    phone: str
    resume_link: str
    applied_on: date


   


@auth.post("/candidates/add/json", response_class=JSONResponse)
def add_candidate(data: CandidateBase):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO candidates (name, email, phone, resume_link, applied_on)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data.name, data.email, data.phone, data.resume_link, data.applied_on
        ))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Candidate added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/candidates/json", response_model=list[CandidateOut])
def get_all_candidates():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM candidates ORDER BY candidate_id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/candidates/{candidate_id}/json", response_model=CandidateOut)
def get_candidate(candidate_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM candidates WHERE candidate_id = %s", (candidate_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Candidate not found")
        return row
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.put("/candidates/{candidate_id}/update/json")
def update_candidate(candidate_id: int, data: CandidateUpdate):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            UPDATE candidates
            SET name = %s, email = %s, phone = %s, resume_link = %s, applied_on = %s
            WHERE candidate_id = %s
        """, (data.name, data.email, data.phone, data.resume_link, data.applied_on, candidate_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Candidate not found")
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Candidate updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/candidates/{candidate_id}/delete/json")
def delete_candidate(candidate_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("DELETE FROM candidates WHERE candidate_id = %s", (candidate_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Candidate not found")
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Candidate deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ApplicationBase(BaseModel):
    job_id: int
    candidate_id: int
    status: str

class ApplicationCreate(BaseModel):
    job_id: int
    candidate_id: int
    status: str
    
@auth.post("/applications/add/json")
def create_application(data: ApplicationCreate):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO applications (job_id, candidate_id, status)
            VALUES (%s, %s, %s)
        """, (data.job_id, data.candidate_id, data.status))

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Application added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ApplicationOut(ApplicationBase):
    app_id: int
    updated_on: datetime

@auth.get("/applications/json", response_model=list[ApplicationOut])
def get_all_applications():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM applications ORDER BY app_id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/applications/{app_id}/json", response_model=ApplicationOut)
def get_application_by_id(app_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM applications WHERE app_id = %s", (app_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            return row
        else:
            raise HTTPException(status_code=404, detail="Application not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ApplicationUpdate(BaseModel):
    status: str 

@auth.put("/applications/{app_id}/update/json")
def update_application(app_id: int, data: ApplicationUpdate):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("""
            UPDATE applications
            SET status = %s, updated_on = CURRENT_TIMESTAMP
            WHERE app_id = %s
        """, (data.status, app_id))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Application not found")

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Application updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth.delete("/applications/{app_id}/delete/json")
def delete_application(app_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()

        cur.execute("DELETE FROM applications WHERE app_id = %s", (app_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Application not found")

        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Application deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SalaryStructureBase(BaseModel):
    position_id: int
    basic: float
    hra: float
    da: float
    allowances: Optional[Dict[str, float]] = {}
    deductions: Optional[Dict[str, float]] = {}
    effective_from: date
    effective_to: Optional[date] = None

class SalaryStructureCreate(BaseModel):
    position_id: int
    basic: float
    hra: float
    da: float
    allowances: Optional[Dict[str, float]] = {}
    deductions: Optional[Dict[str, float]] = {}
    effective_from: date
    effective_to: Optional[date] = None

class SalaryStructureUpdate(BaseModel):
    position_id: int
    basic: float
    hra: float
    da: float
    allowances: Optional[Dict[str, float]] = {}
    deductions: Optional[Dict[str, float]] = {}
    effective_from: date
    effective_to: Optional[date] = None

@auth.post("/salary_structures/add/json")
def add_salary_structure(data: SalaryStructureCreate):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO salary_structures (position_id, basic, hra, da, allowances, deductions, effective_from, effective_to)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.position_id, data.basic, data.hra, data.da,
            json.dumps(data.allowances), json.dumps(data.deductions),
            data.effective_from, data.effective_to
        ))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Salary structure added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SalaryStructureOut(SalaryStructureBase):
    struct_id: int

@auth.get("/salary_structures/json", response_model=list[SalaryStructureOut])
def get_all_salary_structures():
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM salary_structures ORDER BY struct_id")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.get("/salary_structures/{struct_id}/json", response_model=SalaryStructureOut)
def get_salary_structure_by_id(struct_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM salary_structures WHERE struct_id = %s", (struct_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return row
        else:
            raise HTTPException(status_code=404, detail="Salary structure not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@auth.put("/salary_structures/{struct_id}/update/json")
def update_salary_structure(struct_id: int, data: SalaryStructureUpdate):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("""
            UPDATE salary_structures
            SET position_id = %s, basic = %s, hra = %s, da = %s,
                allowances = %s, deductions = %s,
                effective_from = %s, effective_to = %s
            WHERE struct_id = %s
        """, (
            data.position_id, data.basic, data.hra, data.da,
            json.dumps(data.allowances), json.dumps(data.deductions),
            data.effective_from, data.effective_to, struct_id
        ))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Salary structure not found")
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Salary structure updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@auth.delete("/salary_structures/{struct_id}/delete/json")
def delete_salary_structure(struct_id: int):
    try:
        conn = psycopg2.connect(**config())
        cur = conn.cursor()
        cur.execute("DELETE FROM salary_structures WHERE struct_id = %s", (struct_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Salary structure not found")
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Salary structure deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


