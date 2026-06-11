"""Flask web application for generating process diagrams."""

from flask import Flask, render_template, request
from process_diagram import generate_diagram

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    diagram_svg = ""
    process_description = ""

    if request.method == "POST":
        process_description = request.form.get("process_description", "")
        diagram_svg = generate_diagram(process_description)

    return render_template(
        "index.html",
        diagram_svg=diagram_svg,
        process_description=process_description,
    )


if __name__ == "__main__":
    app.run(debug=True)
