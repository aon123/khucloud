from logging import error
from botocore.retries import bucket
from flask import Flask, flash, url_for, render_template, request, redirect, session, jsonify, make_response, Response
from flask.helpers import total_seconds
import pymongo
import string
import random
from functools import wraps
import boto3
from datetime import datetime
import json
from boto3 import client
import re


app = Flask(__name__)
app.config['SECRET_KEY']='fsfjewkjskgkfekfjju345934rsdkfj3t'
myclient = pymongo.MongoClient("mongodb://kloud:khucloudcomputing@3.36.66.92:27017/kloud",authSource="admin")
mydb = myclient['kloud']
userDB = mydb['user']
trashDB = mydb['trash']
bucketDB = mydb["Bucket"]


ACCESS_KEY_ID = ""
ACCESS_SECRET_KEY = ""

sessions = boto3.Session(
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=ACCESS_SECRET_KEY,
)
s3 = sessions.resource('s3')




# Making bytes readible 
def bytes_2_human_readable(number_of_bytes):
    if number_of_bytes < 0:
        raise ValueError("!!! number_of_bytes can't be smaller than 0 !!!")

    step_to_greater_unit = 1024.

    number_of_bytes = float(number_of_bytes)
    unit = 'bytes'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'KB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'MB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'GB'

    if (number_of_bytes / step_to_greater_unit) >= 1:
        number_of_bytes /= step_to_greater_unit
        unit = 'TB'

    precision = 1
    number_of_bytes = round(number_of_bytes, precision)

    return str(number_of_bytes) + ' ' + unit




# Generating id for database user and bucket function
def id_generator(size=10, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


# Checking if user is logged or not if not redirecting to login page
def LoginRequired(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged' in session:
            return f(*args, *kwargs)
        else:
            return redirect(url_for('login')) 
    return wrap
 


###  LOGIN PAGE

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == 'POST':
        user_id = request.form["id"]
        password = request.form["password"]
        find_user = userDB.find_one({"user_id": user_id})
        if find_user is None:
            message = "존재하지 않은 id입니다."
            flash(message)
            return render_template("auth-sign-in.html")
        else:
            if find_user["password"] == password:
                session['user']=find_user["_id"]
                session["logged"] = "logged"
                return redirect(url_for("index"))
            else:
                message = "비밀번호가 일치하지 않습니다."
                flash(message)
                return render_template("auth-sign-in.html")
    else:
        return render_template("auth-sign-in.html")


### REGISTER PAGE

@app.route("/register", methods=["POST","GET"])
def register():
    if request.method == "POST":
        id = id_generator(10)
        user_id = request.form['user_id']
        check_user = userDB.find_one({"user_id": user_id})
        if check_user is None:
            password = request.form['password']
            conf_password = request.form['password_confim']
            if password == conf_password:
                session['user'] = id
                session['logged'] = "logged"
                s3 = sessions.resource('s3')
                s3.create_bucket(
                    ACL='public-read-write',
                    Bucket=id.lower(),
                    CreateBucketConfiguration={
                        'LocationConstraint': 'eu-west-1'
                    },
                )
                userDB.insert_one({"_id":id,"user_id":user_id, "password": password, "bucket_id": id.lower()})
                return redirect(url_for("index"))
            else:
                message = "비밀번호가 일치하지 않습니다."
                flash(message)
                return render_template("auth-sign-up.html")
        else:
            message = "존재하는 id입니다."
            flash(message)
            return render_template("auth-sign-up.html")
    else:
        return render_template("auth-sign-up.html")


### LOGOUT PAGE

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))


### INDEX PAGE 

@app.route("/", methods=["GET", "POST"])
@LoginRequired
def index():
    try:
        trash_active = ""
        my_drive = "active"
        if request.method == "GET":
            user = userDB.find_one({"_id": session["user"]})
            if user is not None:
                bucket = user["_id"].lower()
                x = bucketDB.find_one({"_id": bucket})
                if x is not None:
                    data = x["files"]
                    size = x["size"]
                    unused_size = round(((x['bytes'] / (1024**3))*100)/20)
                    file_len = len(data)     
                else:
                    data = []
                    size = "0"
                    file_len = 0
                    unused_size = 0
            else:
                return redirect(url_for("login"))
            return render_template("page-files.html", data=data, size=size,  file_len = file_len, check_search=False, name=user["user_id"], percentage=unused_size, t=trash_active,m=my_drive)
        else:
            name = request.form['search'].lower()
            user = userDB.find_one({"_id": session["user"]})
            bucket = user["_id"].lower()
            data = []
            size = "0"
            unused_size = 0
            x = bucketDB.find_one({"_id": bucket})
            empty = True
            if x is not None:
                size = x["size"]
                unused_size = round(((x['bytes'] / (1024**3))*100)/20)
                for i in x['files']:
                    pattern = name.lower()
                    print(pattern)
                    match_object = re.search(pattern, i['name'].lower())
                    if match_object:
                        data.append(i)
                        empty = False
            else:
                return redirect(url_for('login'))
            file_len = len(data)
            return render_template("page-files.html", data=data, size=size,  file_len = file_len, check_search=empty,name=user["user_id"], percentage=unused_size,t=trash_active,m=my_drive)
    except Exception as e:
        return render_template("error", error = e)



### UPLOAD PAGE

@app.route("/upload/file", methods=["POST", "GET"])
def upload_file():
    try:
        if request.method=="GET":
            return render_template("page-file-upload.html")
        else:
            if "name" not in request.files:
                return "No user_file key in request.files"
            
            file = request.files["name"]
            size = file.content_length
            print(size)
            name = file.filename
            ftype = file.content_type
            date = datetime.now()
            id = id_generator()
            if file.filename == "":
                return "Please select a file"
            
            bucket = session["user"].lower()
            my_bucket = s3.Bucket(bucket)
            my_bucket.Object(id).put(Body=file, ContentType=ftype, ACL='public-read')
            url = f"https://{bucket}.s3-eu-west-1.amazonaws.com/{id}"
            x = bucketDB.find_one({"_id": bucket})
            if x is not None:
                bucketDB.update_one({"_id": bucket},{"$push": {"files": {"id": id, "name": name, "size": size, "type": ftype, "date": date, "url": url}}})
            else:
                bucketDB.insert_one({"_id": bucket, "files":[{"id": id, "name": name, "size": size, "type": ftype, "date": date, "url": url}], "size":0, "bytes": 0})
            
            x = bucketDB.find_one({"_id": bucket})
            data = x["files"]
            total_size = 0
            for key in my_bucket.objects.all():
                keys = str(key.key)
                print(keys)
                for i in data:
                    if keys == i["id"]:
                        total_size += key.size
                        file_size = bytes_2_human_readable(key.size)
                        bucketDB.update_one({"_id": bucket, "files.id": i["id"]}, {"$set": {"files.$.size": file_size}})
                tsize = bytes_2_human_readable(total_size)
                bucketDB.update_one({"_id": bucket},{"$set": {"size": tsize, "bytes": total_size}})

            return redirect(url_for('index'))
    except Exception as e:
        print(e)
        return e


### TRASH PAGE

@app.route('/trash')
@LoginRequired
def trash():
    try:
        user = userDB.find_one({"_id": session["user"]})
        if user is not None:
            trash_active = "active"
            my_drive = ""
            data = []
            bucket_id = user['_id'].lower()
            get_bucket = bucketDB.find_one({"_id": bucket_id})
            size = get_bucket['size']
            unused_size = round(((get_bucket['bytes'] / (1024**3))*100)/20)
            get_trash = trashDB.find_one({"_id": bucket_id})
            if get_trash is not None:
                for i in get_trash['files']:
                    data.append(i)
                file_len = len(data)
                return render_template('page-delete.html', size=size, file_len=file_len, percentage=unused_size, data=data, name=user['user_id'], check_search=False, t=trash_active, m=my_drive)
            else:
                return render_template('page-delete.html', size=size, file_len=len(data), percentage=unused_size, data=data, name=user['user_id'], check_search=False,t=trash_active, m=my_drive)
        else:
            return redirect(url_for('login'))
    except Exception as e:
        print(e)
        return render_template("error.html", error=e)


### Moving from index page to trash page, bucketDB cleaned from file and moved to trashDB

@app.route('/move/to/trash')
def move_to_trash():
    try:
        if "user" in session:
            id = request.args.get('id')        
            bucket_id = session['user'].lower()
            get_info = bucketDB.find_one({"_id": bucket_id})
            file_info = {}
            for i in get_info['files']:
                if id == i['id']:
                    file_info = i
            if file_info == {}:
                raise Exception
            x = trashDB.find_one({"_id": bucket_id})
            if x is None:
                trashDB.insert_one({"_id": bucket_id, "files": [file_info]})
            else:
                trashDB.update_one({"_id": bucket_id}, {"$push": {"files": file_info}})
            bucketDB.update_one({"_id": bucket_id}, {"$pull": {"files": {"id": id}}})
            return redirect(url_for('index'))
        else:
            return redirect(url_for('login'))
    except Exception as e:
        return render_template('error.html', error=e)


### Deliting file permanently

@app.route("/delete/file/<string:id>")
def delete_file(id):
    try:
        s3 = sessions.resource('s3')
        print(s3)
        bucket = session["user"].lower()
        obj = s3.Object(bucket, id)
        obj.delete()
        trashDB.update_one({"_id": bucket}, {"$pull": {"files": {"id": id}}})
        x = bucketDB.find_one({"_id": bucket})
        data = x["files"]
        total_size = 0
        my_bucket = s3.Bucket(bucket)
        for key in my_bucket.objects.all():
            keys = str(key.key)
            for i in data:
                if keys == i["id"]:
                    total_size += key.size
                    file_size = bytes_2_human_readable(key.size)
                    bucketDB.update_one({"_id": bucket, "files.id": i["id"]}, {"$set": {"files.$.size": file_size}})
            tsize = bytes_2_human_readable(total_size)
            bucketDB.update_one({"_id": bucket},{"$set": {"size": tsize, "bytes": total_size}})
        return redirect(url_for('trash'))
    except Exception as e:
        print(e)
        return e


### Deleting all files from trashDB and bucket

@app.route("/clear/trash/folder", methods=["GET"])
def clear_trash():
    try:
        s3 = sessions.resource('s3')
        bucket = session['user'].lower()
        data = trashDB.find_one({"_id": bucket})
        if data is not None:
            for i in data['files']:
                obj = s3.Object(bucket, i['id'])
                obj.delete()
                trashDB.update_one({"_id": bucket}, {"$pull": {"files": {"id": i['id']}}})
            return redirect(url_for('trash'))
        else:
            print('data empty')
            return redirect(url_for('trash'))
    except Exception as e:
        return render_template('error.html', error=e)


### Restoring from trash to index page

@app.route("/restore/files")
def restore_files():
    try:
        bucket_id = session['user'].lower()
        id = request.args.get('id')
        file_info = {}
        get_info = trashDB.find_one({"_id": bucket_id})
        if get_info is not None:
            for i in get_info['files']:
                if i['id']==id:
                    file_info = i
            if file_info != {}:
                bucketDB.update_one({"_id": bucket_id}, {"$push": {"files": file_info}})
                trashDB.update_one({"_id": bucket_id}, {"$pull": {"files": {"id": i['id']}}})
                return redirect(url_for('trash'))
            else:
                return "Couldn't restore file"
        else:
            return redirect(url_for('login'))
    except Exception as e:
        return render_template('error.html', error=e)



### function to connect to s3

def get_client():
    return client(
        's3',
        'eu-west-1',
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=ACCESS_SECRET_KEY
    )


### Download function 

@app.route("/download")
def download():
    try:
        id = request.args.get('id')
        name = request.args.get('name')
        ftype = request.args.get('type')
        bucket = session["user"].lower()
        s3 = get_client()
        file = s3.get_object(Bucket=bucket, Key=id)
        return Response(
            file['Body'].read(),
            mimetype=ftype,
            headers={"Content-Disposition": f"attachment;filename={name}"}
        )
    except Exception as e:
        print(e)
        return e





if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")