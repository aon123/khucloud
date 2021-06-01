from flask import Flask, flash, url_for, render_template, request, redirect, session, jsonify
from flask.helpers import total_seconds
import pymongo
import string
import random
from functools import wraps
import boto3
from datetime import datetime
import json


app = Flask(__name__)
app.config['SECRET_KEY']='fsfjewkjskgkfekfjju345934rsdkfj3t'
myclient = pymongo.MongoClient("mongodb://kloud:khucloudcomputing@3.36.66.92:27017/kloud",authSource="admin")
mydb = myclient['kloud']
userDB = mydb['user']
trashDB = mydb['trash']
bucketDB = mydb["Bucket"]


ACCESS_KEY_ID = "AKIA5L7BPZG53MID44FP"
ACCESS_SECRET_KEY = "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"

sessions = boto3.Session(
    aws_access_key_id=ACCESS_KEY_ID,
    aws_secret_access_key=ACCESS_SECRET_KEY,
)
s3 = sessions.resource('s3')





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





def id_generator(size=10, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def LoginRequired(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged' in session:
            return f(*args, *kwargs)
        else:
            return redirect(url_for('login')) 
    return wrap
 

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


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))



@app.route("/")
@LoginRequired
def index():
    user = userDB.find_one({"_id": session["user"]})
    if user is not None:
        bucket = user["_id"].lower()
        x = bucketDB.find_one({"_id": bucket})
        if x is not None:
            data = x["files"]
            size = x["size"]
            byte_size = x["bytes"]
            used_size = byte_size/(1024**3)
            file_len = len(data)
            remaining_size = 5-used_size     
        else:
            data = []
            size = "0"
            file_len = 0
            remaining_size = 5
    return render_template("index.html", data=data, size=size, used_size=used_size, file_len = file_len, remaining_size=remaining_size)



@app.route("/upload/file", methods=["POST"])
def upload_file():
    try:
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
        url = f"https://{bucket}.s3-eu-west-1.amazonaws.com/{name}"
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


@app.route("/delete/file/<string:id>")
def delete_file(id):
    try:
        bucket = session["user"].lower()
        obj = s3.Object(bucket, id)
        obj.delete()
        bucketDB.update_one({"_id": bucket}, {"$pull": {"files": {"id": id}}})
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
        return redirect(url_for('index'))
    except Exception as e:
        print(e)
        return e

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")