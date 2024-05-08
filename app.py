from flask import Flask, render_template

app = Flask(__name__)

JOBS = [{"id":1, "role": "Backend Developer", "location": "Remote"},
       {"id":2, "role": "Frontend Developer", "location": "Chennai", "salary": "US$70,000"},
       {"id":3, "role": "Data Scientist", "location": "Bengaluru", "salary": "US$80,000"}]

@app.route("/")
def home():
  return render_template("home.html", jobs=JOBS)

if __name__=="__main__":
  app.run(host = '0.0.0.0',debug=True)