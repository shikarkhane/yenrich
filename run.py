import json
import os

from wms import create_app
# if 'SERVERTYPE' in os.environ and os.environ['SERVERTYPE'] == 'AWS Lambda':


json_data = open('zappa_settings.json')
env_vars = json.load(json_data)['dev']['environment_variables']
for key, val in env_vars.items():
    os.environ[key] = val

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=int(os.environ.get('PORT', 8080)))
