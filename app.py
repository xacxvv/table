"""Flask application for viewing EduPage timetables."""
from __future__ import annotations

import json
from typing import Dict, List

from flask import Flask, abort, render_template, request

import parsers


app = Flask(__name__)


def _load_all_data() -> Dict[str, object]:
    classes_data = parsers.load_classes()
    teachers_data = parsers.load_teachers()
    days: List[str] = classes_data.get("days") or teachers_data.get("days")
    periods: List[str] = classes_data.get("periods") or teachers_data.get("periods")
    return {
        "classes": classes_data,
        "teachers": teachers_data,
        "days": days,
        "periods": periods,
    }


data_store = _load_all_data()


@app.context_processor
def inject_globals():
    return {
        "days": data_store["days"],
        "periods": data_store["periods"],
    }


@app.route("/")
def index():
    classes_data = data_store["classes"]
    teachers_data = data_store["teachers"]
    school_to_classes = classes_data["school_to_classes"]
    schools = classes_data["schools"]
    teacher_names = teachers_data["teacher_names"]
    return render_template(
        "index.html",
        schools=schools,
        school_to_classes_json=json.dumps(school_to_classes, ensure_ascii=False),
        teacher_names=teacher_names,
    )


@app.route("/class")
def class_timetable():
    class_name = request.args.get("class_name")
    if not class_name:
        abort(404)
    classes_data = data_store["classes"]
    if class_name not in classes_data["class_names"]:
        abort(404)
    odd_week = classes_data["odd_week"].get(class_name, [])
    even_week = classes_data["even_week"].get(class_name, [])
    return render_template(
        "class_timetable.html",
        class_name=class_name,
        odd_week=odd_week,
        even_week=even_week,
    )


@app.route("/teacher")
def teacher_timetable():
    teacher_name = request.args.get("teacher_name")
    if not teacher_name:
        abort(404)
    teachers_data = data_store["teachers"]
    if teacher_name not in teachers_data["teacher_names"]:
        abort(404)
    odd_week = teachers_data["odd_week"].get(teacher_name, [])
    even_week = teachers_data["even_week"].get(teacher_name, [])
    return render_template(
        "teacher_timetable.html",
        teacher_name=teacher_name,
        odd_week=odd_week,
        even_week=even_week,
    )


if __name__ == "__main__":
    # Development entry point. For network access use:
    #   flask run --host 0.0.0.0 --port 5000
    app.run(debug=True)
