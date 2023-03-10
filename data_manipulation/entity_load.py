#%%
from google.cloud import pubsub_v1
publisher = pubsub_v1.PublisherClient()
#%%
isLocal=False
#%%
import certifi
import requests
import json
from urllib import parse
import pymongo
import time
import copy
from bson.objectid import ObjectId
import base64
m_db=pymongo.MongoClient("mongodb+srv://$USER:$PASS@$DB.$KEY.mongodb.net/", tlsCAFile=certifi.where())

def pubsub(topic_name,message):
    if isLocal:
        return LOCALpubsub(topic_name,message)
    
    topic_path = publisher.topic_path("total-scion-368611", topic_name)
    message_json = json.dumps({"data":message} )
    message_bytes = message_json.encode('utf-8')
    try:
        publish_future = publisher.publish(topic_path, data=message_bytes)
        publish_future.result()  # Verify the publish succeeded
        return 'Message published.'
    except Exception as e:
        print(e)
        return (e, 500)

def LOCALpubsub(topic_name,message):
    url = "https://us-central1-total-scion-368611.cloudfunctions.net/pubsub"
    payload = json.dumps({
    "topic": topic_name,
    "message": message
    })
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)

#%%
def fancyString(raw):
    print("RAW",raw)
    if type(raw)!=list:
        s_list=[raw]
    else:
        s_list=copy.deepcopy(raw)
    s_final=""
    for s in s_list:  
        words = s.split("_")
        first_word=words[0].capitalize()
        if len(words)>1:
            first_word=first_word+" "
        cap = first_word + " ".join(map(lambda x:x.capitalize(),words[1:]))
        if s_final=="":
            s_final=copy.deepcopy(cap)
        else:
            s_final=s_final+", "+copy.deepcopy(cap)
    return s_final

def entityContributions(fide_id):
    contributions_final={}
    other_doc_keys=['fide_id','names','type','images']
    
    conts_to=m_db["entity_db"]["contributions"].find({"from.document.fide_id":fide_id,"from.collection":"entities"})
    experience=[]
    for cont_to in conts_to:
        doc_filter={}
        if cont_to['to']['document'].get('_id'):
            doc_filter['_id']=ObjectId(cont_to['to']['document']['_id'])
        elif cont_to['to']['document'].get('fide_id'):
            doc_filter['fide_id']=cont_to['to']['document']['fide_id']
            
        other_doc=m_db['entity_db']['entities'].find_one(doc_filter)
        if other_doc.get('links') and other_doc.get('names')==None:# if time_update is old?
            if other_doc['links'].get('messari') or other_doc['links'].get('twitter'):
                #might need to check entity
                pass
        
        elif other_doc:
            other_doc_final={}
            for key in other_doc_keys:
                if other_doc.get(key):
                    other_doc_final[key]=other_doc[key]
            
            if cont_to.get('tags'):
                if cont_to['tags'].get('roles'):
                    other_doc_final['roles']=fancyString(cont_to['tags']['roles'])
            
            if cont_to.get('times'):
                other_doc_final['times']=cont_to['times']

                
            experience.append(other_doc_final)
    if experience!=[]:
        contributions_final['experience']=experience
    
    conts_from=m_db["entity_db"]["contributions"].find({"to.document.fide_id":fide_id,"to.collection":"entities","tags.roles":"team_member"})
    family=[]
    team=[]
    for cont_from in conts_from:
        doc_filter={}
        if cont_from['from']['document'].get('_id'):
            doc_filter['_id']=ObjectId(cont_from['from']['document']['_id'])
        elif cont_from['from']['document'].get('fide_id'):
            doc_filter['fide_id']=cont_from['from']['document']['fide_id']
            
        other_doc=m_db['entity_db']['entities'].find_one(doc_filter)
        if other_doc.get('links') and other_doc.get('names')==None:# if time_update is old?
            if other_doc['links'].get('messari') or other_doc['links'].get('twitter'):
                #might need to check entity
                pass
        
        elif other_doc:
            if other_doc.get('type') in ['project','organization']:
                family_doc_final={}
                for key in other_doc_keys:
                    if other_doc.get(key):
                        family_doc_final[key]=other_doc[key]
               
                if cont_from.get('tags'):
                    if cont_from['tags'].get('roles'):
                        family_doc_final['roles']=fancyString(cont_from['tags']['roles'])
                
                if cont_from.get('times'):
                    family_doc_final['times']=cont_from['times']
                
                family.append(family_doc_final)
                
            else:
                team_doc_final={}
                for key in other_doc_keys:
                    if other_doc.get(key):
                        team_doc_final[key]=other_doc[key]
                
                if cont_from.get('tags'):
                    if cont_from['tags'].get('roles'):
                        team_doc_final['roles']=fancyString(cont_from['tags']['roles'])
                
                if cont_from.get('times'):
                    team_doc_final['times']=cont_from['times']
                    
                team.append(team_doc_final)
            
    if team!=[]:
        contributions_final['team']=team
    if family!=[]:
        contributions_final['family']=family
        
        
    locations_from=m_db["entity_db"]["contributions"].find({"from.document.fide_id":fide_id,"from.collection":"source","from.document.type":"location"})

    locations=[]  
    for location in locations_from:
        other_doc=m_db['entity_db']['sources'].find_one({"_id":ObjectId(location['from']['document']['_id'])})
        if other_doc:
            other_doc_final={}
            for key in other_doc_keys:
                if other_doc.get(key):
                    other_doc_final[key]=other_doc[key]
            locations.append(other_doc_final)
    if locations!=[]:
        contributions_final['locations']=locations
    
    return contributions_final

def fullEntity(fide_id):
    entity_final=m_db["entity_db"]["entities"].find_one({"fide_id":fide_id})
    if entity_final.get('tags'):
        tags_dict={}
        for tag_key in entity_final['tags']:
            tags_dict[tag_key]=fancyString(entity_final['tags'][tag_key])
            
        entity_final['tags']=tags_dict
    
    if entity_final.get('times'):
        entity_time=entity_final['times']
        if entity_time.get('start'):
            entity_time['start_str']=time.strftime('%m-%d-%Y', time.localtime(entity_time['start']))
        
        entity_final['times']=entity_time
    
    if entity_final.get('team_size'):
        team_size=entity_final['team_size']
        if team_size.get('count') and team_size.get('range') and team_size.get('range')!=0:
            s_low=team_size.get('count')-team_size.get('range')
            s_high=team_size.get('count')+team_size.get('range')
            team_size['range_str']=str(s_low)+"-"+str(s_high)+" people"
        elif team_size.get('count'):
            team_size['range_str']=str(team_size.get('count'))+" people"
        entity_final['team_size']=team_size
    
    entity_contributions=entityContributions(fide_id)
    entity_final['contributions']=entity_contributions#removed if statement
    
    del entity_final['_id']
    del entity_final['time_updated']
    del entity_final['time_created']
    del entity_final['revision']
    
    return entity_final

#%%
# fide_id="f3365482381"
# fullEntity(fide_id)
#%%

def entityLoad(request):
    request_json = request.get_json(silent=True)
    topic_name = request_json.get("topic")
    message = request_json.get("message")
    if not topic_name or not message:
        return ('Missing "topic" and/or "message" parameter.', 400)
    print(f'Getting ent message to topic {topic_name}')

    
    try:
        if topic_name=="full_entity":
            fide_id=message['fide_id']
            return_me=fullEntity(fide_id)
        else:
            return_me="topic unknown: "+topic_name
        return return_me
    except Exception as e:
        print(e)
        return (e, 500)
    
# %%
