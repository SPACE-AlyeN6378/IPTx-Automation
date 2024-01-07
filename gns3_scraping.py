import requests
import xml.etree.ElementTree as Tree
from router import Router
from typing import Tuple

gns3_server = 'http://localhost:3080'
gns3_api_base = f'{gns3_server}/v2'

# Get the project from the user
projects_url = f'{gns3_api_base}/projects'
proj_response = requests.get(projects_url)
projects_data = proj_response.json()

# Check if the response is accepted
if proj_response.status_code != 200:
    raise ConnectionError(f"Error: {proj_response.status_code} - {proj_response.content}")


# First a user selects a project from a list of projects
def select_project_from_user():
    print("Select Project by number:")
    for index, project in enumerate(projects_data):
        print(f"    {index + 1}. {project['name']}")

    print()

    selected = 0
    while not (1 <= selected <= len(projects_data)):
        try:
            selected = int(input("> "))

            if not (1 <= selected <= len(projects_data)):
                print(f"ERROR: Invalid selection '{selected}'")

        except ValueError:
            print(f"ERROR: Please type in any number from 1 to {len(projects_data)}")

    return projects_data[selected - 1]


# Determine if a point is inside the rectangle
def inside_rectangle(given_point: Tuple[int, int], rect_pos: Tuple[int, int], width: int, height: int):
    x_lb = rect_pos[0]  # Lower bound of X
    x_ub = x_lb + width  # Upper bound of X
    y_lb = rect_pos[1]  # Lower bound of Y
    y_ub = y_lb + height  # Upper bound of Y

    return (x_lb <= given_point[0] <= x_ub) and (y_lb <= given_point[1] <= y_ub)


# Determine if a point is inside the ellipse
def inside_ellipse(given_point: Tuple[int, int], ellipse_pos: Tuple[int, int], width: int, height: int):
    # Using the equation (x - h)^2 / a^2 + (y - k)^2 / b^2 = 1
    a = width / 2
    b = height / 2
    h = ellipse_pos[0] + a
    k = ellipse_pos[1] + b
    x, y = given_point

    return ((x - h) ** 2 / a ** 2) + ((y - k) ** 2 / b ** 2) <= 1


# Determine if the object is within the area
def inside_given_area(drawing_json, node):
    svg = drawing_json["svg"]
    root = Tree.fromstring(svg)
    given_point = (node.x, node.y)
    drawing_pos = (drawing_json['x'], drawing_json['y'])

    if root.find('rect'):
        rectangle = root.find('rect')
        width = int(rectangle.get('width'))
        height = int(rectangle.get('height'))

        return inside_rectangle(given_point, drawing_pos, width, height)

    elif root.find('ellipse'):
        width = int(root.get('width'))
        height = int(root.get('height'))

        return inside_ellipse(given_point, drawing_pos, width, height)

    else:
        raise TypeError("The drawing should either be a rectangle or an ellipse")


def get_device(node_json: dict):
    node_id = node_json['node_id']
    hostname = node_json['name']
    interfaces = node_json[]
    return Router(node_json['node_id'], )


def get_nodes(project_id):
    nodes_url = f'{projects_url}/{project_id}/nodes'
    response = requests.get(nodes_url)
    nodes_data = response.json()

    return nodes_data


PROJECT_ID = "99dab476-e669-4463-bb47-62d3241e55d1"
for node in get_nodes(PROJECT_ID):
    print(node["name"])
