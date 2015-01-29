#!/usr/bin/env python

import csv
import json

CSV_FOLDER_PATH = "../data/"


def clean(name):
    return name.rpartition('_')[-1].replace(' ', '').lower()


def generate_course_structure():

    def get_structure_from(filepath):
        structure = {"children": {}, "parent": {}, "base": {}}

        def check_n_append_child(key, child):
            if child not in structure["children"][key]:
                structure["children"][key].append(child)

        def check_n_init_children(key):
            if key not in structure["children"]:
                structure["children"][key] = []

        def check_n_add_parent(key, parent):
            if key not in structure["parent"]:
                structure["parent"][key] = parent

        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                id = clean(row["id"])
                section = clean(row["section"])
                subsection = clean(row["subsection"])
                base = int(row["max_points"]) if "max_points" in row else int(row["duration_seconds"])
                check_n_init_children("overall")
                check_n_init_children(section)
                check_n_init_children(subsection)
                check_n_append_child("overall", section)
                check_n_append_child(section, subsection)
                check_n_append_child(subsection, id)
                check_n_add_parent(section, "overall")
                check_n_add_parent(subsection, section)
                check_n_add_parent(id, subsection)
                if subsection in structure["base"]:
                    structure["base"][subsection][id] = base
                else:
                    structure["base"][subsection] = {id: base}

        return structure

    return {"video": get_structure_from(CSV_FOLDER_PATH + "videos.csv"),
            "problem": get_structure_from(CSV_FOLDER_PATH + "problems.csv")}


def generate_students_data(course_structure):

    students = {}

    def get_student_data_from(filepath, category):

        def aggregate(l):
            return reduce(lambda a, b: [a[0] + b[0], a[1] + b[1]], l)

        def get_score(l):
            return round(float(l[0]) / l[1], 3)

        def get_donut(d):
            return {k: [get_score(x) for x in d[k]] for k in d}

        def get_report(d):
            return {k: get_score(aggregate(d[k])) for k in d}

        def update_data(category, current_student_id, current_student):
            if current_student_id in students and category in students[current_student_id]:
                student_temp = students[current_student_id][category]["donut"]
            else:
                if current_student_id not in students:
                    students[current_student_id] = {category: {}}
                else:
                    students[current_student_id][category] = {}
                student_temp = course_structure[category]["children"].copy()
            for key in student_temp:
                if key in current_student:
                    vals = [current_student[key][x] if x in current_student[key] else [0, course_structure[category]["base"][key][x]] for x in student_temp[key]]
                elif key.startswith("lecture"):
                    vals = [[0, course_structure[category]["base"][key][x]] for x in student_temp[key]]
                else:
                    vals = student_temp[key]
                student_temp[key] = vals
            for key in student_temp:
                if key.startswith("week"):
                    vals = [aggregate(student_temp[x]) for x in student_temp[key]]
                    student_temp[key] = vals
            student_temp["overall"] = [aggregate(student_temp[x]) for x in student_temp["overall"]]

            students[current_student_id][category]["donut"] = get_donut(student_temp)
            students[current_student_id][category]["report"] = get_report(student_temp)

        with open(filepath) as f:
            reader = csv.DictReader(f)
            current_student_id = 0
            current_student = {}
            for row in reader:
                student_id = int(clean(row["student_id"]))
                section = clean(row["section"])
                subsection = clean(row["subsection"])
                if "video_id" in row:
                    id = clean(row["video_id"])
                    score = [int(row["watched_seconds"]), int(row["duration_seconds"])]
                elif "problem_id" in row:
                    id = clean(row["problem_id"])
                    score = [int(row["score"]), int(row["max_points"])]

                if student_id == current_student_id:
                    # update current student
                    if subsection not in current_student:
                        current_student[subsection] = {id: score}
                    else:
                        current_student[subsection][id] = score

                else:
                    # put back in students
                    update_data(category, current_student_id, current_student)
                    # init new student
                    current_student_id = student_id
                    current_student = {subsection: {id: score}}
            # dont forget last student
            update_data(category, current_student_id, current_student)

    def fill_holes():

        def empty(d):
            return {"donut": {k: [0 for i in d[k]] for k in d}, "report": {k: 0 for k in d}}

        empty_problem = empty(course_structure["problem"]["children"])
        empty_video = empty(course_structure["video"]["children"])
        for student_id in students:
            if "problem" not in students[student_id]:
                students[student_id]["problem"] = empty_problem
            if "video" not in students[student_id]:
                students[student_id]["video"] = empty_video

    def get_avg():

        def add_list(l1, l2):
            return [l1[i] + l2[i] for i in range(len(l1))]

        def deep_add(a, b):
            result = {"video": {"report": {}, "donut": {}}, "problem": {"report": {}, "donut": {}}}
            for category in ["problem", "video"]:
                for result_type in ["report", "donut"]:
                    for key in a[category][result_type]:
                        x = a[category][result_type][key]
                        y = b[category][result_type][key]
                        if type(x) == float:
                            result[category][result_type][key] = x + y
                        elif type(x) == list:
                            result[category][result_type][key] = add_list(x, y)
            return result

        def deep_div(a, n):
            result = {"video": {"report": {}, "donut": {}}, "problem": {"report": {}, "donut": {}}}
            for category in ["problem", "video"]:
                for result_type in ["report", "donut"]:
                    for key in a[category][result_type]:
                        x = a[category][result_type][key]
                        if type(x) == float:
                            result[category][result_type][key] = round(x / n, 3)
                        elif type(x) == list:
                            result[category][result_type][key] = [round(e / n, 3) for e in x]
            return result

        students["avg"] = deep_div(reduce(deep_add, students.values()), len(students))

    get_student_data_from(CSV_FOLDER_PATH + "problem_attempts.csv", "problem")
    get_student_data_from(CSV_FOLDER_PATH + "video_views.csv", "video")
    fill_holes()
    get_avg()

    return students


if __name__ == "__main__":
    cs = generate_course_structure()
    with open("_courseStructure.json", "w") as fout:
        json.dump(cs, fout)
    with open("_students.json", "w") as fout:
        json.dump(generate_students_data(cs), fout)