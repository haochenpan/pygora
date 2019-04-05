from base64 import b64encode, b64decode
from hashlib import md5
from logging import getLogger, Formatter, FileHandler, StreamHandler, DEBUG, INFO
from lxml.etree import HTML
from os import path, getcwd
from requests import Session
from sys import stdout
from time import time, sleep

TERM = '2020F'  # 2019F -> Fall 2018, 2019S -> Spring 2019, 2020F -> Fall 2019, ...
SUBJECT_URL = ('https://services.bc.edu/courseinfosched/courseinfoschedResults!displayInput.action?'
               f'keyword=&presentTerm=&registrationTerm=&termsString=&selectedTerm={TERM}'
               '&selectedSchool={}&selectedSubject={}&selectedLevel=All')
COURSE_URL = ('https://services.bc.edu/courseinfosched/main/courseinfoschedResults!'
              f'displayOneCourseMethod.action?courseKey={TERM}'
              '+{}&presentTerm=')
url1 = 'https://login.bc.edu/nidp/idff/sso?sid=0&sid=0&Ecom_User_ID={}&Ecom_Password={}'
url2 = 'https://login.bc.edu/nidp/app/login?id=10&sid=0&option=credential&sid=0'
url3 = 'https://login.bc.edu/nidp/app/login?sid=0&sid=0'
url4 = SUBJECT_URL.format('2MCAS', '2BIOL')
CRE_PATH = path.join(getcwd(), 'cre')


def set_credential(username, password):
    """
    hashes and locally stores a username and a password to CRE_PATH
    :param username: a valid Agora username
    :param password: corresponding password
    :return:
    """
    with open(CRE_PATH, 'wb') as f:
        usr = b64encode(username.encode())
        pwd = b64encode(password.encode())
        f.write(usr + " ".encode() + pwd)
        print("the credential has been locally stored as a hash")


def get_credential():
    """
    reads locally stored username and password at CRE_PATH
    :return: raise FileNotFoundError and exits if no credential pair has ever been set
             otherwise returns a tuple, in the form of (username, password)
    """
    try:
        with open(CRE_PATH, 'rb') as f:
            ln = f.read().split(' '.encode())
            usr = b64decode(ln[0]).decode()
            pwd = b64decode(ln[1]).decode()
            return usr, pwd
    except FileNotFoundError:
        LOG.exception("not credential has been locally stored")
        exit(1)


def get_logger(logger_name, debug=True, log_file_name='pygora.log'):
    """
    a logger factory used by pygora and could be used elsewhere
    :param logger_name:
    :param debug: if True, it does console output & file output, otherwise only file output
    :param log_file_name:
    :return:
    """
    logger = getLogger(logger_name)
    fmtter = Formatter('%(levelname)s %(asctime)s %(name)s %(lineno)d: %(message)s')
    file_handler = FileHandler(log_file_name)
    file_handler.setFormatter(fmtter)
    logger.addHandler(file_handler)
    logger.setLevel(INFO)

    if debug:
        # to handle the screen output
        console_handler = StreamHandler(stdout)
        console_handler.setFormatter(fmtter)
        logger.addHandler(console_handler)
        logger.setLevel(DEBUG)

    return logger


def get_session(username: str, password: str, check_valid=False):
    """
    tries to establish a client session with Agora Portal
    :param username: a valid Agora username
    :param password: corresponding password
    :param check_valid: if True, check the establish session really works
                        by visiting a sample page
    :return: normally returns a (requests.Session, generate_time) tuple
             if session is not established / asked to check valid by fails
             returns a (None, 0) tuple
    """
    try:
        session = Session()
        session.get(url1.format(username, password))
        session.get(url2)
        session.get(url3)
    except Exception as e:
        LOG.exception(f"get_session raises an exception")
        return None, 0

    if check_valid and not _is_session_valid(session):
        LOG.exception(f"get_session raises an exception")
        return None, 0

    return session, int(time())


def get_sessions(count=1):
    """
    batch generate sessions
    :param count: the number of sessions needs to be generated
    :return: normally, a tuple of two lists, ([session_list], [gen_times])
             if a session is not established / asked to check valid by fails
             exit with code 2
    """
    sessions, gen_times = [], []
    cre = get_credential()
    for _ in range(count):
        session, gen_time = get_session(*cre)
        if gen_time == 0:
            LOG.exception("the session is not valid")
            exit(2)
        sessions.append(session)
        gen_times.append(gen_time)
    return sessions, gen_times


def are_sessions_valid(sessions: list, gen_times: list, strong=False):
    """
    check whether sessions are valid in program runtime
    :param sessions: a session list returned by get_sessions
    :param gen_times: a gen_time list returned by get_sessions
    :param strong: whether need to check the session really works
    :return: a boolean indicates if all of sessions are valid
    """
    # weak validity: session are generated in less than 30 mins
    for gen_time in gen_times:
        if gen_time + 1800 <= int(time()):
            return False

    # strong validity: sessions are actually working
    if strong:
        for session in sessions:
            if not _is_session_valid(session):
                return False

    return True


def download_subjects(session, simple=False):
    resp = session.get(url4)  # or any other subject
    html = HTML(resp.text)
    school_list = html.xpath('//li[@id="school"]/ul')[0]
    school_names = school_list.xpath('./li/label/text()')
    school_codes = school_list.xpath('./li/input/@value')
    subject_list = html.xpath('//li[@id="subject"]/ul')[0]
    subject_names = subject_list.xpath('./li/label/text()')
    subject_codes = subject_list.xpath('./li/input/@value')

    subject_dict_list = []
    for i, each_subject in enumerate(subject_codes):
        if i == 0 or each_subject[0] == 'X':  # excludes "all" and summer school options
            continue

        for j, each_school in enumerate(school_codes):
            if each_school.startswith(each_subject[0]):
                url, md5 = _get_subject_url_and_md5(each_school, each_subject)
                if simple:
                    subject_dict = each_school + " " + each_subject + " " + url
                else:
                    subject_dict = {
                        "_id": md5,
                        "term": TERM,
                        "school_name": school_names[j],
                        "school_code": each_school,
                        "subject_name": subject_names[i],
                        "subject_code": each_subject,
                        "subject_url": url
                    }
                subject_dict_list.append(subject_dict)
                break

    return subject_dict_list


def parse_subject_page(response):
    time_stamp = int(time())
    course_dict_list = []

    try:
        html = HTML(response.text)
        course_count = html.xpath('//form[@id="courseInfoSchedResults"]/'
                                  'header/div/div[1]/h2/span/text()')
        assert len(course_count) == 1, "Search Results (155 Courses)"
        course_count = str(course_count[0])
        course_count = str(course_count[course_count.find('(') + 1:course_count.find(')')]).split(" ")[0]
        course_count = int(course_count)
        courses = html.xpath('//div[@id="resultTableBody"]/table/'
                             'tbody/tr/td[@style="width: 440px;"]')
        assert len(courses) == course_count, "table entries # should match course_count"
    except Exception:
        LOG.exception(f"subject_fetcher_thread, error fetching: \n{response.url}")
        sleep(3)
        return course_dict_list

    # iterate through every course (courses could be empty when course_count==0)
    for course in courses:
        title = course.xpath('./a/span/strong/text()')[0]
        code = title[title.rfind('(') + 1:title.rfind(')')]
        alert = course.xpath('./div[@class="alert"]')
        if len(alert) > 0:
            alert = 'CLOSED'
        else:
            alert = 'OPEN'
        url, md5 = _get_course_url_and_md5(code)
        course_dict = {
            "_id": md5,
            "term": TERM,
            "title": title,
            "code": code,
            "alert": alert,  # <-
            "start": time_stamp,
            "end": time_stamp,
            "url": url
        }
        course_dict_list.append(course_dict)
    return course_dict_list


def parse_course_page(response, info_dict):
    try:
        html = HTML(response.text)
        information = html.xpath('//*[@id="courseinfoschedHome"]/div/div/div/div')
        assert len(information) == 15
    except Exception:
        LOG.exception(f"subject_fetcher_thread, error fetching: \n{response.url}")
        sleep(3)
        return

    for i, each in enumerate(information):
        if i == 3:  # term
            pass
        elif i == 0:
            each = _clr_str(each)
            info_dict['schoolFull'] = each[len('School '):]
        elif i == 1:
            each = _clr_str(each)
            info_dict['department'] = each[len('Department '):]
        elif i == 2:
            fs = each.xpath('./a')
            info_dict['faculties'] = [f.xpath('string(.)').replace('\xa0', '') for f in fs]
        elif i == 4:
            each = _clr_str(each)
            info_dict["maximumSize"] = int(each[len('Maximum Size '):])
        elif i == 5:
            each = each.xpath('./div[@class="schedule"]')[0]

            info_dict["day"] = []
            info_dict["time"] = []
            info_dict["location"] = []

            # if the schedule is by arrangement
            uls = each.xpath('./ul')
            if not uls:
                s = _clr_str(each)
                info_dict["day"].append(' '.join(s.split()))
                continue

            # schedule
            for ul in uls:
                day_list = []
                if ul.xpath('li[@class="meet monday"]'):
                    day_list.append("Mon")
                if ul.xpath('li[@class="meet tuesday"]'):
                    day_list.append("Tue")
                if ul.xpath('li[@class="meet wednesday"]'):
                    day_list.append("Wed")
                if ul.xpath('li[@class="meet thursday"]'):
                    day_list.append("Thu")
                if ul.xpath('li[@class="meet friday"]'):
                    day_list.append("Fri")
                info_dict["day"].append(' '.join(day_list))

            # time
            for t in each.xpath('./span[@class="time"]'):
                info_dict["time"].append(_clr_str(t))

            # location
            for l in each.xpath('./span[@class="location"]'):
                info_dict["location"].append(_clr_str(l))
        elif i == 6:
            each = _clr_str(each)
            info_dict["credits"] = int(each[len("Credits "):])
        elif i == 7:
            each = _clr_str(each)
            info_dict["level"] = each[len("Level "):]
        elif i == 8:
            # description
            each = _clr_str(each)
            info_dict["description"] = each[len("Description "):].strip()

            # message
            message = html.xpath('//div[@class="message col-xs-11 col-sm-11 '
                                 'col-md-11 col-lg-11 pull-right"]')
            if not message:
                info_dict["message"] = []
            else:
                message = message[0].xpath('string(.)')
                message = message.split("\n")
                message = [each.strip() for each in message]
                message = [each for each in message if each]
                info_dict["message"] = message
        elif i == 9:
            each = _clr_str(each)
            info_dict["prerequisites"] = each[len("Prerequisites "):]
        elif i == 10:
            each = _clr_str(each)
            info_dict["corequisites"] = each[len("Corequisites "):]
        elif i == 11:
            each = _clr_str(each)
            info_dict["crossListings"] = each[len("Cross Listings "):]
        elif i == 12:
            each = _clr_str(each)
            info_dict["courseIndex"] = each[len("Course Index "):]
        elif i == 13:
            each = _clr_str(each)
            info_dict["frequency"] = each[len("Frequency "):]
        elif i == 14:
            each = _clr_str(each)
            info_dict["repeatable"] = each[len("Repeatable "):]


def _is_session_valid(session):
    text = session.get(url4).text
    return 'studentservices@bc.edu' in text


def _clr_str(path):
    """
    a private method that strips a xpath to a string
    :param path:
    :return:
    """
    return path.xpath('string(.)').strip()


def _get_md5(url):
    h1 = md5()
    h1.update(url.encode(encoding='utf-8'))
    return h1.hexdigest()


def _get_subject_url_and_md5(school, subject):  # school: 2MCAS, subject: 2CSCI
    url = SUBJECT_URL.format(school, subject)
    return url, _get_md5(url)


def _get_course_url_and_md5(course):  # course: CSCI110101
    url = COURSE_URL.format(course)
    return url, _get_md5(url)


LOG = get_logger("pygora")

if __name__ == '__main__':
    pass
