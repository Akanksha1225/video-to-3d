from flask import Flask, request, jsonify, Response
from flask_restx import Api, Resource, reqparse, fields
from werkzeug.datastructures import FileStorage
from lumaapi import LumaClient
import os
import requests

app = Flask(__name__)
api = Api(app, version='1.0', title='Luma API Gateway', description='A simple API gateway for Luma API')

# Luma API Client Initialization
luma_client = LumaClient(api_key='a8783b5f-42ea-45c0-8fc4-dab307e73147-ae4d630-d216-4526-b93d-01968f1c79da')  # Replace with your actual Luma API key

ns = api.namespace('luma', description='Luma operations')

upload_parser = reqparse.RequestParser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='File to be uploaded')
upload_parser.add_argument('title', type=str, required=False, default='Untitled', help='Title of the upload')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'zip'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Set the directory for file uploads
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@ns.route('/upload')
class FileUpload(Resource):
    @ns.expect(upload_parser)
    def post(self):
        args = upload_parser.parse_args()
        uploaded_file = args['file']
        title = args['title']

        if uploaded_file and allowed_file(uploaded_file.filename):
            filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(filepath)

            slug = luma_client.submit(filepath, title)
            return {'slug': slug}, 200
        else:
            return {'message': 'File type not allowed'}, 400

file_status = api.model('FileStatus', {
    'slug': fields.String(required=True, description='Slug of the uploaded file')
})

@ns.route('/status')
class FileStatus(Resource):
    @api.expect(file_status)
    def post(self):
        data = request.json
        slug = data.get('slug')

        if not slug:
            return {'message': 'Slug is required'}, 400

        try:
            luma_capture_info = luma_client.status(slug)
            # Assuming luma_capture_info can be serialized directly
            return jsonify(luma_capture_info), 200
        except Exception as e:
            return {'error': str(e)}, 500

@ns.route('/download/<slug>')
class DownloadCapture(Resource):
    def get(self, slug):
        auth_headers = {'Authorization': 'luma-api-key=a8783b5f-42ea-45c0-8fc4-dab307e73147-ae4d630-d216-4526-b93d-01968f1c79da'}
        download_url = f"https://webapp.engineeringlumalabs.com/api/v2/capture/{slug}/download"
        response = requests.get(download_url, headers=auth_headers, stream=True)

        def generate():
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk

        return Response(generate(), headers={
            'Content-Disposition': f'attachment;filename={slug}.zip',
            'Content-Type': 'application/zip'
        })

@ns.route('/capture-status/<slug>')
class CaptureStatus(Resource):
    def get(self, slug):
        auth_headers = {'Authorization': 'luma-api-key=a8783b5f-42ea-45c0-8fc4-dab307e73147-ae4d630-d216-4526-b93d-01968f1c79da'}
        response = requests.get(f"https://webapp.engineeringlumalabs.com/api/v2/capture/{slug}",
                                headers=auth_headers)
        return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)
