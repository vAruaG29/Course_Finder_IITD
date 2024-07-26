from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import warnings
from urllib3.exceptions import InsecureRequestWarning
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def get_course_links(base_url):
    try:
        response = requests.get(base_url, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return [requests.compat.urljoin(base_url, link['href'])
                for link in soup.select('table a[href]')]
    except requests.RequestException:
        return []

def get_students_in_course(course_url):
    try:
        response = requests.get(course_url, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return {cols[0].get_text().strip(): cols[1].get_text().strip()
                for cols in (row.find_all('td') for row in soup.select('table tr')[1:]) if len(cols) >= 2}
    except requests.RequestException:
        return {}

def find_student_courses(base_url, student_entry_or_name):
    course_links = get_course_links(base_url)
    student_courses = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_course = {executor.submit(get_students_in_course, url): url for url in course_links}
        for future in as_completed(future_to_course):
            course_url = future_to_course[future]
            try:
                students = future.result()
                if student_entry_or_name in students.values() or student_entry_or_name in students:
                    course_name = course_url.split('/')[-1].replace('.shtml', '')
                    student_courses.append(course_name)
            except Exception:
                pass
                
    return student_courses

def filter_courses_by_code(courses, code_prefix):
    return [course for course in courses if course.startswith(code_prefix)]

def get_filtered_courses(base_url, student1, code_prefix, student2=None):
    courses1 = find_student_courses(base_url, student1)
    filtered_courses1 = filter_courses_by_code(courses1, code_prefix)
    if student2:
        courses2 = find_student_courses(base_url, student2)
        filtered_courses2 = filter_courses_by_code(courses2, code_prefix)
        return set(filtered_courses1).intersection(filtered_courses2)
    return filtered_courses1

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        mode = int(request.form.get('mode'))
        check = int(request.form.get('check'))
        
        if check:
            student1 = request.form.get('student1')
        else:
            student1 = request.form.get('kerberos_id1')

        code_prefix = request.form.get('Semester_Code (e.g. 2301)')
        
        if mode == 0:
            if check:
                student2 = request.form.get('student2')
            else:
                student2 = request.form.get('kerberos_id2')
            result = get_filtered_courses(base_url, student1, code_prefix, student2)
        else:
            result = get_filtered_courses(base_url, student1, code_prefix)
    
    return render_template('index.html', result=result)

if __name__ == "__main__":
    base_url = 'https://ldapweb.iitd.ac.in/LDAP/courses/'
    app.run(debug=True)
