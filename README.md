# pygora
#### A web crawler library that fetches and parses data from [BC Agora Portal](https://services.bc.edu/commoncore/myservices.do).

## Getting started (Python 3):
```
pip install pygora-phchcc
```

## Examples
##### log in agora, download and print links to all subject pages
```python
from pygora import *

session, gen_time = get_session("myAgoraUsername", "myAgoraPassword", check_valid=True)
# if gen_time == 0, we know something goes wrong (maybe you did not input the correct credential)
print(gen_time)

subjects = download_subjects(session, simple=True)  # simple: each subject is a string
for i, line in enumerate(subjects):
    print(i, line)
    
# subjects = download_subjects(session) #eacg subject is a dict, with more information

```

##### cache the username and password so that you don't have to write them explicitly in a script
```python
from pygora import *

# to set credential, run it once so that username & password are stored locally
set_credential("myAgoraUsername", "myAgoraPassword")

# to clear out credential
set_credential("", "")

```

##### example of `parse_subject_page`: print out all biology courses (school and subject codes can be found in `subject.txt`), provided that if you have run `set_credential`
```python
from pygora import *

session, gen_time = get_session(*get_credential(), check_valid=True)
# if you are confident that your username & password are correct, do
# session, gen_time = get_session(*get_credential())

url = SUBJECT_URL.format('2MCAS', '2BIOL')  # get you a url string
resp = session.get(url)  # use your session to HTTP get the url
courses = parse_subject_page(resp)  # parse the subject page
for course in courses:
    print(course)

```


##### example of `parse_course_page`: print all information on a course page (the course code can be found in the output of `parse_subject_page`)
```python
from pygora import *

session, gen_time = get_session(*get_credential())
url = COURSE_URL.format('ACCT102101')

# a dummy dict in this example, could be your data fetched from database
info_dict = dict()
resp = session.get(url)
parse_course_page(resp, info_dict)  # update the dict
for key, value in info_dict.items():
    print(key, value)

```

## Related Projects
##### the backend of [EagleVision](http://www.eaglevisionapp.com/)
##### the backend of [New PEPS (planning)]()

## Join Dev Team / Contact Us:
##### open an issue on Github to announce the feature/bug that you want to work on
##### or through email: (Haochen) phchcc_at_gmail_dot_com 
##### or search our names in BC directory

## Special Thanks
##### Special thanks to people who made EagleVision (this project's prototype) and pygora alive (names are listed in alphabetical order):
[Baichuan (Patrick) Guo]() -- the original "Honest Team" <br>
[David Shen]() -- the EagleVision Dev Team <br>
[Estevan Feliz](http://estevanfeliz.me/) -- the original "Honest Team" & the EagleVision Dev Team <br>
[Roger Wang](https://rogerwangcs.com/) -- the EagleVision Dev Team  <br>
[Yuning (Tommy) Yang]() -- the original "Honest Team" <br>
[Yuxuan (Jacky) Jin](https://github.com/PolarCapital) -- the EagleVision Dev Team <br>
