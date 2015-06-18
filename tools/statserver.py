
from flask import Flask, request
import argparse
import ujson as json

app = Flask(__name__)

@app.route('/collect', methods=['POST'])
def collect():
    data = request.get_json()
    if sanity_check_data(data):
        with open(app.config['TARGET'], 'a') as target:
            target.write(request.data + '\n')
        return 'Thank you'
    else:
        return 'Missing mandatory arguments', 400


def sanity_check_data(data):
    required_properties = (
        'audio',
        'video',
        'connection',
        'timestamp',
    )
    if data and isinstance(data, list):
        for report in data:
            if not all(key in report for key in required_properties):
                return False
        return True
    return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', help='Where to store incoming data',
        default='data.dat')
    parser.add_argument('-d', '--debug', default=False, action='store_true')
    args = parser.parse_args()
    app.config['TARGET'] = args.target
    app.run(host='0.0.0.0', port=9000, debug=args.debug)
