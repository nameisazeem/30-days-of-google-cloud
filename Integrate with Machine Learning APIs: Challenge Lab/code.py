<___________________________Code to add _____________________________>


import os
import sys

from google.cloud import storage, bigquery, language, vision, translate_v2

if ('GOOGLE_APPLICATION_CREDENTIALS' in os.environ):
    if (not os.path.exists(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])):
        print ("The GOOGLE_APPLICATION_CREDENTIALS file does not exist.\n")
        exit()
else:
    print ("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not defined.\n")
    exit()

if len(sys.argv)<3:
    print('You must provide parameters for the Google Cloud project ID and Storage bucket')
    print ('python3 '+sys.argv[0]+ '[PROJECT_NAME] [BUCKET_NAME]')
    exit()

project_name = sys.argv[1]
bucket_name = sys.argv[2]

storage_client = storage.Client()
bq_client = bigquery.Client(project=project_name)
nl_client = language.LanguageServiceClient()

vision_client = vision.ImageAnnotatorClient()
translate_client = translate_v2.Client()

dataset_ref = bq_client.dataset('image_classification_dataset')
dataset = bigquery.Dataset(dataset_ref)
table_ref = dataset.table('image_text_detail')
table = bq_client.get_table(table_ref)

rows_for_bq = []

files = storage_client.bucket(bucket_name).list_blobs()
bucket = storage_client.bucket(bucket_name)

print('Processing image files from GCS. This will take a few minutes..')

for file in files:    
    if file.name.endswith('jpg') or  file.name.endswith('png'):
        file_content = file.download_as_string()
        
        from google.cloud import vision_v1 as vision
        import io
        client = vision.ImageAnnotatorClient()


        image = vision.types.Image(content=file_content)
        response = client.text_detection(image=image)
    
        text_data = response.text_annotations[0].description

        file_name = file.name.split('.')[0] + '.txt'
        blob = bucket.blob(file_name)
        blob.upload_from_string(text_data, content_type='text/plain')

        desc = response.text_annotations[0].description
        locale = response.text_annotations[0].locale
        
     
        if locale == 'en':
            translated_text = desc
        else:
            from google.cloud import translate_v2 as translate
            
            client = translate.Client()
            translation = translate_client.translate(text_data, target_language='en')
            translated_text = translation['translatedText']
        print(translated_text)
        
        if len(response.text_annotations) > 0:
            rows_for_bq.append((desc, locale, translated_text, file.name))

print('Writing Vision API image data to BigQuery...')
errors = bq_client.insert_rows(table, rows_for_bq)

assert errors == []
