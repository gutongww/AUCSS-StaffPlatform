from datetime import *
from flask import *
from werkzeug.security import generate_password_hash, check_password_hash
from config import db
from meeting import *
from sponsor import *
import random
import config
from leave import *

app = Flask(__name__)

app.config.from_object(config)


# App init====================================================================================================
@app.route('/', methods=['POST'])
def login_page():
        email = request.form.get('email')
        password = request.form.get('password')
        if not all([email, password]):
            flash("Please fill in the information completely！")
        try:
            cur = db.cursor()
            sql = "select password from user where email = '%s'" % email
            db.ping(reconnect=True)
            cur.execute(sql)
            result = cur.fetchone()
            if result is None:
                flash("User does not exist！")
                return render_template('index.html')
            if check_password_hash(result[0], password):
                session['email'] = email
                session.permanent = True
                return dashbord()
            else:
                flash("Incorrect password!")
                return render_template('index.html')
        except Exception as e:
            raise e


# Login status maintained
@app.context_processor
def login_status():
    # from session get email
    email = session.get('email')
    # If there is email information, it proves that you are logged in, and we
    # get the nickname and user type of the logon from the database to return to the global
    if email:
        try:
            cur = db.cursor()
            sql = "select name,department,type from user where email = '%s'" % email
            db.ping(reconnect=True)
            cur.execute(sql)
            result = cur.fetchone()
            if result:
                return {'email': email, 'name': result[0], 'department': result[1], 'type': result[2]}
        except Exception as e:
            raise e
    # If email information does not exist, no login, return empty
    return {}

@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='GET':
        return render_template('register.html')
    elif request.method=='POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password_1 = request.form.get('password_1')
        password_2 = request.form.get('password_2')
        code = request.form.get('code')
        type = 0
        department = ''

        # Incomplete information
        if not all([email, name, password_1, password_2]):
            flash("Incomplete information, please complete the form.")
            return redirect(url_for('register'))

        # Password inconsistent
        if password_1 != password_2:
            flash("Password entries are inconsistent.")
            return redirect(url_for('register'))

        # Hash password
        password = generate_password_hash(password_1, method="pbkdf2:sha256", salt_length=8)

        # 检查邀请码，部门分类
        if code == 'AUCSSHR2020':  # 人力资源部
            department = 'HR'
            type = 2
        elif code == 'AUCSSPR2020':  # 外联部
            department = 'PR'
            type = 3
        elif code == 'AUCSSEP2020':  # 策划部
            department = 'EP'
            type = 4
        elif code == 'AUCSSMKT2020':  # 市场部
            department = 'MKT'
            type = 5
        elif code == 'AUCSSOP2020':  # 运营支持部
            department = 'OP'
            type = 6
        elif code == 'AUCSSSUPER':  # 主席团
            department = 'SUPER'
            type = 7
        else:
            flash("Password entries are inconsistent.")
            return redirect(url_for('register'))

        try:
            cur = db.cursor()
            sql = "select * from user where email = '%s'" % email
            db.ping(reconnect=True)
            cur.execute(sql)
            result = cur.fetchone()
            if result is not None:
                flash("This email has been registered")
                return render_template('index.html')
            else:
                sql = "insert into user(Name,email,password,department,type) VALUES ('%s','%s','%s','%s',%s)" % (
                    name, email, password, department, type)
                db.ping(reconnect=True)
                cur.execute(sql)
                db.commit()
                cur.close()
                return redirect(url_for('dashbord'))

        except Exception as e:
            raise e



@app.route('/', methods=['GET'])
def dashbord():
    login_ = login_status()
    if len(login_) == 0:
        return render_template('index.html')
    else:
        meetings = list_meeting_of_user(login_['email'])
        data = [login_['name'], meetings, str(len(meetings))]  # data=[0=email,1=meetings,2=len(meetings)]
        if login_['type'] == 1:  # Category 1: General Staff
            return render_template('backend.html', user_name=data[0], issue_information=data)
        if login_['type'] == 2:  # Category 2: HR Staff
            return hr(data)
        if login_['type'] == 3:  # Category 3: PR Staff
            return pr(data)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for(('dashbord')))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500


@app.route('/favicon.ico')
def favicon():
    return 'a'


@app.route('/meetingleave', methods=['GET'])
def meeting_leave():
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    if request.method == 'GET':
        info = ''
        info1 = ''
        meetings = list_meeting_of_user(login_['email'])
        if len(meetings) == 0:
            info = "You don't have meetings at the moment where you can ask for leave."
        all_leaves = list_leave_apply_of_user(login_['email'])
        if len(all_leaves) == 0:
            info1 = "You haven't asked for leave yet!"

        if login_['type']==2:
            return render_template('MeetingLeave.html', info=info, info1=info1, meetings=meetings, leaves=all_leaves,
                                   user_name=login_['name'])
        elif login_['type']==3:
            return render_template('MeetingLeavePR.html', info=info, info1=info1, meetings=meetings, leaves=all_leaves,
                                   user_name=login_['name'])


@app.route('/meetingleave', methods=['POST'])
def apply_for_leave():
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    reason = request.form.get('reason')
    meeting_id = request.form.get('radio1')
    email = login_['email']
    apply_leave(email, meeting_id, reason)
    return redirect(url_for(('meeting_leave')))


# Page for department of HR ====================================================================================
@app.route('/hr')
def hr(issu):
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    return render_template('HRadmin.html', user_name=issu[0], issue_information=issu)


@app.route('/meetings', methods=['GET'])
def manag_meeting():
    login_ = login_status()
    if len(login_) == 0:
        return dashbord()
    user = login_status()
    meetings = list_all_meetings()
    issu = [user['name'], meetings]
    return render_template('ManageMeetings.html', issue_information=issu, user_name=login_['name'])


@app.route('/meetings', methods=['POST'])
def add_meeting():
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    location = request.form.get('location')
    title = request.form.get('title')
    date = request.form.get('date').split("-")
    time = request.form.get('time')
    id = int(str(date[2] + date[1] + date[0]) + str(random.randrange(100, 999)))
    meeting_ids = get_all_meeting_id()
    while id in meeting_ids:
        id = int(date.replace('-', '') + str(random.randrange(100, 999)))
    datatime = date[2] + "-" + date[1] + "-" + date[0] + " " + time + ":00"
    sql = "INSERT INTO meeting(meeting_id,meeting_title,meeting_location,meeting_date) " \
          "VALUES (%s,'%s','%s','%s')" % (id, title, location, datatime)

    edit_meeting_to_database(sql)
    add_all_staff_to_meeting(id)
    return redirect(url_for(('manag_meeting')))


@app.route('/<mid>', methods=['GET', 'POST'])
def edit_meeting(mid):
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    if request.method == 'GET':
        try:
            cur = db.cursor()
            sql = "select * from meeting where meeting_id=%s" % mid
            db.ping(reconnect=True)
            cur.execute(sql)
            meeting = cur.fetchall()
            title = meeting[0][1]
            location = meeting[0][2]
            datetime = meeting[0][3]
            date = datetime.strftime("%x")
            time = datetime.strftime("%X")[:-3]
            return render_template('EditMeeting.html', user_name=login_['name'], mid=mid, title=title,
                                   location=location, date=date, time=time)
        except Exception as e:
            raise e
    elif request.method == 'POST':
        try:
            location = request.form.get('location')
            title = request.form.get('title')
            date = request.form.get('date').split("/")
            time = request.form.get('time')
            datatime = "20" + date[2] + "-" + date[1] + "-" + date[0] + " " + time + "00"
            sql = "update meeting set meeting_title='%s',meeting_location='%s',meeting_date='%s' where meeting_id=%s" % (
                title, location, datatime, mid)
            edit_meeting_to_database(sql)
            return manag_meeting()
        except Exception as e:
            raise e


@app.route('/<mid>/delmeeting', methods=['GET'])
def del_meeting(mid):
    sql = 'delete from meeting where meeting_id=%s' % mid
    edit_meeting_to_database(sql)
    return redirect(url_for(('manag_meeting')))


@app.route('/manageleaves', methods=['GET'])
def manage_leave():
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    all_leaves = list_all_leave_requests()
    leaves_record=list_all_records()
    return render_template('ManageLeave.html', user_name=login_['name'], leaves=all_leaves, leaves_record=leaves_record)


@app.route('/<mid>/<email>/decline', methods=['GET'])
def decline_leave(mid, email):
    login_ = login_status()
    if len(login_) == 0:
        return redirect((url_for('dashbord')))
    decline_status(mid, email)
    return redirect(url_for('manage_leave'))


@app.route('/<mid>/<email>/approve', methods=['GET'])
def approve_leave(mid, email):
    login_ = login_status()
    if len(login_) == 0:
        return redirect((url_for('dashbord')))
    approve_status(mid, email)
    processor=login_['name']
    add_leave_to_leave_history(mid,email,processor)
    return redirect(url_for('manage_leave',))


# Page for department of PR ====================================================================================
@app.route('/pr',methods=['GET'])
def pr(issu):
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))

    return render_template('PRadmin.html', user_name=login_['name'],issue_information=issu)

@app.route('/sponsordatabase',methods=['GET','POST'])
def sponsor_database():
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    if request.method=='GET':
        sponsors=list_all_sponsors()
        return render_template('SponsorsDatabase.html',user_name=login_['name'],sponsors=sponsors)

    if request.method=='POST':
        sponsor_name=request.form.get('sponsor_name')
        sponsor_add=request.form.get('sponsor_add')
        contact_name=request.form.get('contact_name')
        contact=request.form.get('contact')
        contact_type=request.form.get('contact_type')
        staff=request.form.get('staff')
        sponsor_comment=request.form.get('sponsor_comment')
        sql="INSERT INTO sponsors (sponsor_name,sponsor_add,contact_name,contact,contact_type,staff,sponsor_comment)" \
            "VALUES ('%s','%s','%s','%s','%s','%s','%s')"%(sponsor_name,sponsor_add,contact_name,contact,contact_type,staff,sponsor_comment)
        add_sponsor(sql)
        return redirect(url_for('sponsor_database'))

@app.route('/editsponsorsid<sid>',methods=['GET','POST'])
def edit_sponsor(sid):
    login_ = login_status()
    if len(login_) == 0:
        return redirect(url_for(('dashbord')))
    if request.method=='GET':
        that_sponsor=get_sponsor(sid)
        return render_template('EditSponsor.html',user_name=login_['name'],sponsor=that_sponsor)
    elif request.method=='POST':
        try:
            sponsor_name = request.form.get('sponsor_name')
            sponsor_add = request.form.get('sponsor_add')
            contact_name = request.form.get('contact_name')
            contact = request.form.get('contact')
            contact_type = request.form.get('contact_type')
            staff = request.form.get('staff')
            sponsor_comment = request.form.get('sponsor_comment')
            sql = "UPDATE sponsors " \
                  "SET sponsor_name='%s',sponsor_add='%s',contact_name='%s',contact='%s',contact_type='%s',staff='%s',sponsor_comment='%s'" \
                  "WHERE sponsor_id=%s" % (
                  sponsor_name, sponsor_add, contact_name, contact, contact_type, staff, sponsor_comment, sid)
            add_sponsor(sql)
            return redirect(url_for("sponsor_database"))
        except Exception as e:
            raise e



@app.route('/deletesponsor<sid>',methods=['GET'])
def delete_sponsor(sid):
    sql = 'delete from sponsors where sponsor_id=%s' % sid
    add_sponsor(sql)
    return redirect(url_for(('sponsor_database')))


# Page for department of EP ====================================================================================

if __name__ == '__main__':
    app.run()
