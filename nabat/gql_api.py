import requests
import json


class GraphQL_API:

    def __init__(self, url="https://api.sciencebase.gov/nabat-graphql/graphql"):
        # def __init__(self, url="http://localhost:8080/graphql"):
        self.gql = Gql(url)
        self.sample_frames = [{"name": "Continental US", "description": "10x10km Grid", "id": 14, "center": [39.833333, -98.583333], "zoom":4, "pThreshold":6714, "layer":"nabat:clipped_conus_3857", "crs":"+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=23 +lon_0=-96 +x_0=0 +y_0=0 +ellps=GRS80 +towgs84=1,1,-1,0,0,0,0 +units=m +no_defs", "cellCount":133807}, {"name": "Hawaii", "description": "5x5km Grid", "id": 15, "center": [20.9502, -156.73166], "zoom":7, "layer":"nabat:clipped_hawaii_3857", "crs":"+proj=aea +lat_1=8 +lat_2=18 +lat_0=13 +lon_0=-157 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs", "cellCount":877}, {"name": "Canada", "description": "10x10km Grid", "id": 19, "center": [62.716667, -97.916667], "zoom":4,
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      "layer":"nabat:clipped_canada_3857", "crs":"+proj=longlat +datum=WGS84 +no_defs", "cellCount":106558}, {"name": "Alaska", "description": "10x10km Grid", "id": 20, "center": [64.731667, -152.47], "zoom":4, "layer":"nabat:clipped_alaska_3857", "crs":"+proj=longlat +datum=WGS84 +no_defs", "cellCount":40414}, {"name": "Mexico", "description": "10x10km Grid", "id": 12, "center": [20.520556, -99.895833], "zoom":5, "layer":"nabat:clipped_mex_3857", "crs":"+proj=longlat +datum=WGS84 +no_defs", "cellCount":20599}, {"name": "Puerto Rico", "description": "5x5km Grid", "id": 21, "center": [18.226944, -66.391111], "zoom":8, "layer":"nabat:clipped_pr_3857", "crs":"+proj=longlat +datum=WGS84 +no_defs", "cellCount":442}]

    def upload_gottbat_detection(self, fileName, recordingTime, grtsId, gottbatDetectorId, speciesId, confidence, pulseCount, meanFrequency):
        query = """
           mutation uploadGottbatDetectionMutation($input: UploadGottbatDetectionInput!) {
                uploadGottbatDetection(input: $input) {
                    success
                }
            }
            """
        variables = {"input": {"fileName": fileName, "recordingTime": recordingTime, "grtsId": grtsId, "gottbatDetectorId": gottbatDetectorId,
                               "speciesId": speciesId, "confidence": confidence, "pulseCount": pulseCount, "meanFrequency": meanFrequency}}

        response = self.gql.query(query=query, variables=variables)
        if response and response['data']:
            return response['data']['uploadGottbatDetection']
        raise Exception("Unable to upload gottbat detection")

    def search_lat_long(self, latitude, longitude):
        query = """
            query fnPublicSearchFeatureGeom($geom1: GeoJSON!, $geom2: JSON!) {
                fnPublicSearchFeatureGeom(search: $geom1) {
                    nodes {
                        type
                        class
                        description
                        id
                        name
                    }
                }
                grtsSelectionSearch(geom: $geom2) {
                    nodes {
                        grtsId
                        grtsCellId
                        sampleFrameId
                    }
                }
            }
            """
        # types are different so need the var listed twice :(
        variables = {
            "geom1": {
                'type': 'Point',
                'crs': {'type': 'name', 'properties': {'name': 'EPSG:4326'}},
                'coordinates': [
                    longitude,
                    latitude
                ]
            }, "geom2": {
                'type': 'Point',
                'crs': {'type': 'name', 'properties': {'name': 'EPSG:4326'}},
                'coordinates': [
                    longitude,
                    latitude
                ]
            }
        }

        try:
            response = self.gql.query(query=query, variables=variables)
            result = {}
            if response and response['data'] and response['data']['grtsSelectionSearch']['nodes'] and len(response['data']['grtsSelectionSearch']['nodes']):
                result = {
                    'grtsId': response['data']['grtsSelectionSearch']['nodes'][0]['grtsId'],
                    'grtsCellId': response['data']['grtsSelectionSearch']['nodes'][0]['grtsCellId'],
                    'sampleFrame': self._sample_frame_name_from_id(response['data']['grtsSelectionSearch']['nodes'][0]['sampleFrameId'])
                }
            for r in response['data']['fnPublicSearchFeatureGeom']['nodes']:
                if r['class'] == 'U.S. States and Territories':
                    result['state'] = r['name']
                elif r['class'] == 'U.S. Counties':
                    result['county'] = r['name']

            return result
        except Exception as e:
            print(e)
            raise Exception(
                "API lookup failed. Unable to get location from latitude + longitude")

    def get_species_list(self, grts_id):
        query = """
           query allGrtsSpeciesRangeBuffered($grtsId: Int!) {
                allGrtsSpeciesRangeBuffereds(filter: { grtsId: { equalTo: $grtsId } }) {
                    nodes {
                    grtsId
                    speciesId
                    speciesCode
                    }
                }
            }
            """
        variables = {"grtsId": grts_id}

        response = self.gql.query(query=query, variables=variables)
        if response and response['data'] and response['data']['allGrtsSpeciesRangeBuffereds']['nodes'] and len(response['data']['allGrtsSpeciesRangeBuffereds']['nodes']):
            return [node['speciesCode'] for node in response['data']['allGrtsSpeciesRangeBuffereds']['nodes']]

        raise Exception("API lookup failed. No Results for this location")

    def get_survey_event_by_identifier(self, identifier):
        query = """
           query getSurveyEventDetails($identifier: UUID!) {
                getSurveyEventDetails(identifier: $identifier) {
                    grtsId
                    grtsCellId
                    sampleFrameId
                    startTime
                    locationName
                }
            }
            """
        variables = {"identifier": identifier}

        response = self.gql.query(query=query, variables=variables)
        if response and response['data'] and response['data']['getSurveyEventDetails']:
            response['data']['getSurveyEventDetails']['sampleFrame'] = self._sample_frame_name_from_id(
                response['data']['getSurveyEventDetails']['sampleFrameId'])
            return response['data']['getSurveyEventDetails']
        raise Exception("API lookup failed. No Results for this identifier")

    def _sample_frame_name_from_id(self, sample_frame_id):
        for sf in self.sample_frames:
            if sf['id'] == sample_frame_id:
                return sf['name']

    def _sample_frame_id_from_name(self, sample_frame_name):
        for sf in self.sample_frames:
            if sf['name'] == sample_frame_name:
                return sf['id']

    def get_sample_frame_names(self):
        return [sf['name'] for sf in self.sample_frames]


class Gql():
    def __init__(self, url):
        self.url = url

    def query(self, query, variables):

        data = {"query": query, "variables": json.dumps(variables)}
        response = requests.post(self.url, data=data)
        return response.json()
