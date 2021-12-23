from flask import Flask, render_template, request, jsonify
import os
import random

from stringAlg import StringAlg, ThreadingWrapper

exporting_threads = {}
app = Flask(__name__)
app._static_folder = os.path.abspath("static/")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/fileUpload", methods=["POST", "GET"])
def fileUpload():
    if request.method == "POST":
        data = request.form

        global exporting_threads

        thread_id = random.randint(0, 10000)
        exporting_threads[thread_id] = ThreadingWrapper(data['numPins'], data['maxLines'], data['lineWeight'], data['image'])
        exporting_threads[thread_id].start()
        print(jsonify(thread_id = thread_id))
        return jsonify(thread_id = thread_id)

    return render_template("index.html")

@app.route("/progress/<int:thread_id>")
def progress(thread_id): 
    global exporting_threads

    return str(exporting_threads[thread_id].getProgress())

@app.route("/line_sequence/<int:thread_id>")
def line_sequence(thread_id): 
    global exporting_threads
    
    return jsonify(line_sequence = exporting_threads[thread_id].getLineSequence())

if __name__ == "__main__":
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    app.run(debug=True)