import streamlit as st
import numpy as np
import pandas as pd
import json, rdflib, os , requests
from rdflib import URIRef, Literal, Namespace, Graph , plugin , ConjunctiveGraph
from rdflib.plugins.sparql import prepareQuery
from rdflib.namespace import RDF , RDFS, DC , XSD
from rdflib.serializer import Serializer
import altair as alt
from collections import defaultdict
from itertools import groupby
from SPARQLWrapper import SPARQLWrapper
from requests.auth import HTTPBasicAuth

@st.cache
def parse_data():
    ###############################
    #####    PARSE DATA     #######
    ###############################

    @st.cache
    def load_gam_catalogue_data():
        """get museum cataloguing data"""

        sour = requests.get("https://raw.githubusercontent.com/marilenadaquino/spiceboard/main/demonstrator/rdf_transform/GAM_test_catalogue.json").json()

        # with open(source) as f:
        #    sour = json.load(f)

        catalogue = []
        # key = 	"f6b5743b-220c-4802-8163-7c9de0d6c56d"
        #
        # sour = requests.get('https://api2.mksmart.org/browse/f1f1018c-6e72-4e95-953e-889d9ae0c914', auth=HTTPBasicAuth(key, key)).json()
        #
        gam_game_list = defaultdict(list)
        for entity in sour["@graph"]:
            # get gam sessions
            if "class" in entity and entity["class"] == "fc:FruitionContext":
                if isinstance(entity["artefact"],list):
                    for session in entity["artefact"]:
                        gam_game_list[entity["uri"]].append(session["uri"])

                if isinstance(entity["artefact"],dict):
                    gam_game_list[entity["uri"]].append(entity["artefact"]["uri"])
        gam_game_list = dict(gam_game_list)
        for entity in sour["@graph"]:
            # get artefacts
            if "class" in entity and "Artefact" in entity["class"]:
                artefact = {}
                artefact["ID"] = entity["uri"].split("/")[-1]
                artefact["title"] = entity["schema:headline"] if "schema:headline" in entity else "NO TITLE"
                cr_uri = entity["schema:creator"]["uri"] if "schema:creator" in entity else "NO AUTHOR"
                creator = [ creat["label"] for creat in sour["@graph"] if creat["uri"] == cr_uri ]
                artefact["author"] = creator[0] if len(creator) > 0 else "NO AUTHOR"
                artefact["description"] = entity["schema:abstract"] if "schema:abstract" in entity else ""
                artefact["date"] = entity["schema:dateCreated"]["value"][:10] if "schema:dateCreated" in entity else "2010-00-00"
                artefact["image"] = [ img["image_url"]["uri"] for img in sour["@graph"] if ("documented_in" in entity and img["uri"] == entity["documented_in"]["uri"])]

                if "narrative:hasRepresentedAction" in entity and isinstance(entity["narrative:hasRepresentedAction"],list):
                    artefact["actions"] = [ act["label"] \
                                for act in sour["@graph"] \
                                for ent in entity["narrative:hasRepresentedAction"] \
                                if (act["uri"] == ent["uri"])]
                if "narrative:hasRepresentedAction" in entity and isinstance(entity["narrative:hasRepresentedAction"],dict):
                    artefact["actions"] = [ act["label"] \
                                for act in sour["@graph"] \
                                if (act["uri"] == entity["narrative:hasRepresentedAction"]["uri"])]

                if "narrative:hasRepresentedEntity" in entity and isinstance(entity["narrative:hasRepresentedEntity"],list):
                    artefact["entities"] = [ act["label"] \
                                for act in sour["@graph"] \
                                for ent in entity["narrative:hasRepresentedEntity"] \
                                if (act["uri"] == ent["uri"])]
                if "narrative:hasRepresentedEntity" in entity and isinstance(entity["narrative:hasRepresentedEntity"],dict):
                    artefact["entities"] = [ act["label"] \
                                for act in sour["@graph"] \
                                if (act["uri"] == entity["narrative:hasRepresentedEntity"]["uri"])]
                # statements on feelings or emotions
                if "subject" in entity and isinstance(entity["subject"],list):
                    artefact["emotions"] = [ act["content"] \
                                for act in sour["@graph"] \
                                for ent in entity["subject"] \
                                if (act["uri"] == ent["uri"])]
                if "subject" in entity and isinstance(entity["subject"],dict):
                    artefact["emotions"] = [ act["content"] \
                                for act in sour["@graph"] \
                                if (act["uri"] == entity["subject"]["uri"])]

                # annotated emotions emotion:triggers
                if "emotion:triggers" in entity and isinstance(entity["emotion:triggers"],list):
                    artefact["annotated_emotions"] = [ act["class"].split("emotion:")[1] \
                                for act in sour["@graph"] \
                                for ent in entity["emotion:triggers"] \
                                if (act["uri"] == ent["uri"])]
                if "emotion:triggers" in entity and isinstance(entity["emotion:triggers"],dict):
                    artefact["annotated_emotions"] = [ act["class"].split("emotion:")[1] \
                                for act in sour["@graph"] \
                                if (act["uri"] == entity["emotion:triggers"]["uri"])]
                tweets , insta = [] , []
                if "subject_of" in entity and isinstance(entity["subject_of"],list):
                    tweets = [user_act for user_act in entity["subject_of"] if "twitter" in user_act['uri']]
                    insta = [user_act for user_act in entity["subject_of"] if "instagram" in user_act['uri']]

                if "subject_of" in entity and isinstance(entity["subject_of"],dict):
                    tweets = [entity["subject_of"]["uri"]] if "twitter" in entity["subject_of"]["uri"] else []
                    insta = [entity["subject_of"]["uri"]] if "instagram" in entity["subject_of"]["uri"] else []

                art_uri = entity["uri"]
                gam_sessions = [session for session,artefacts in gam_game_list.items() if art_uri in artefacts]
                artefact["twitter"] = len(tweets)
                artefact["instagram"] = len(insta)
                artefact["gam_sessions"] = len(gam_sessions)
                catalogue.append(artefact)
        return catalogue

    data = load_gam_catalogue_data()

    @st.cache
    def load_gam_twitter_data(data):
        """get twitter data"""

        # TODO change with API
        sour = requests.get("https://raw.githubusercontent.com/marilenadaquino/spiceboard/main/demonstrator/rdf_transform/GAM_test_twitter.json").json()
        # with open(source) as f:
        #    sour = json.load(f)
        # key = 	"f6b5743b-220c-4802-8163-7c9de0d6c56d"
        #
        # sour = requests.get('https://api2.mksmart.org/browse/74270a7b-d9f6-4b15-b7dc-4246505cb409', auth=HTTPBasicAuth(key, key)).json()

        twitter_data = []
        for entity in sour["@graph"]:
            if "class" in entity and entity["class"] == "SocialMediaPosting":
                tweet = {}
                tweet["date"] = entity["datePublished"]["value"][:10] if "datePublished" in entity else "2010-00-00"
                tweet["url"] = entity["schema:url"]["uri"]
                tweet["img"] = [im["uri"] for im in entity["sharedContent"] if im["uri"].endswith("jpg")]

                tweet_uri = [im["uri"] for im in entity["sharedContent"] if im["uri"].endswith("text")][0]
                tweet["txt"] = [ent["content"] for ent in sour["@graph"] if ent["uri"] == tweet_uri and "content" in ent][0] if tweet_uri else ""

                art_id = entity["about"]["uri"].split("/")[-1]
                artefact = [art["title"] for art in data if art["ID"] == art_id][0]
                tweet["artefact"] = str(artefact)
                twitter_data.append(tweet)
        return twitter_data

    twitter_data = load_gam_twitter_data(data)

    @st.cache
    def load_gam_instagram_data(data):
        """get instagram data"""
        # TODO change with API
        sour = requests.get("https://raw.githubusercontent.com/marilenadaquino/spiceboard/main/demonstrator/rdf_transform/GAM_test_instagram.json").json()
        # with open(source) as f:
        #    sour = json.load(f)
        # key = 	"f6b5743b-220c-4802-8163-7c9de0d6c56d"
        #
        # sour = requests.get('https://api2.mksmart.org/browse/a098187d-e5e0-4be8-9961-4e92918cf32a', auth=HTTPBasicAuth(key, key)).json()
        instagram_data = []
        for entity in sour["@graph"]:
            if "class" in entity and entity["class"] == "SocialMediaPosting":
                post = {}
                post["date"] = entity["datePublished"]["value"][:10] if "datePublished" in entity else "2010-00-00"
                post["url"] = entity["schema:url"]["uri"]
                post["img"] = [im["uri"] for im in entity["sharedContent"] if not im["uri"].endswith("text")]
                post_uri = [im["uri"] for im in entity["sharedContent"] if im["uri"].endswith("text")][0]

                txt = [ent["content"] for ent in sour["@graph"] if (ent["uri"] == post_uri and "content" in ent) ]
                post["txt"] = txt[0] if len(txt) > 0 else ""
                art_id = entity["about"]["uri"].split("/")[-1]
                artefact = [art["title"] for art in data if art["ID"] == art_id][0]
                post["artefact"] = str(artefact)
                instagram_data.append(post)

        return instagram_data

    instagram_data = load_gam_instagram_data(data)

    @st.cache
    def load_gamgame_data(data):
        """get GAM game data"""
        # TODO change with API
        sour = requests.get("https://raw.githubusercontent.com/marilenadaquino/spiceboard/main/demonstrator/rdf_transform/GAMgame.json").json()
        # with open(source) as f:
        #     sour = json.load(f)

        game_data_list = []
        for entity in sour["@graph"]:
            if "class" in entity and entity["class"] == "Action" and entity["executes"]["uri"] == "https://w3id.org/spice/manifest/00003_user_picture_selection":
                game_data = {}
                cur_picture = entity["generated"]["uri"]
                # TO BE CHANGED
                cur_art_id = entity["generated"]["uri"].split("/img_1")[0].split("https://w3id.org/spice/gam/artefact/")[1]
                title = [art["title"] for art in data if art["ID"] == cur_art_id][0]
                session_id = entity["uri"].split("/")[-1]
                next_text_action = entity["script:precedes"]["uri"]
                txt_uri = [ act["generated"]["uri"] for act in sour["@graph"] if act["uri"] == next_text_action and "generated" in act]
                text = [act["content"] for act in sour["@graph"] if (len(txt_uri)>0 and act["uri"] == txt_uri[0] and "content" in act)  ]
                next_emo_action = [ act["script:precedes"]["uri"] for act in sour["@graph"] if (act["uri"] == next_text_action and "script:precedes" in act)][0]
                next_emo_uri = [emo_act["generated"]["uri"] for emo_act in sour["@graph"] if (emo_act["uri"] == next_emo_action and "generated" in emo_act)]
                emo_text = [emo_text["content"] for emo_text in sour["@graph"] if (len(next_emo_uri)>0 and emo_text["uri"] == next_emo_uri[0] and "content" in emo_text)  ]
                date = [ act["date_time"][0]["value"] \
                        for act in sour["@graph"] \
                        if (act["uri"] == entity["at_time"]["uri"] \
                        and "class" in act \
                        and act["class"] == "dul:TimeInterval") ]
                game_data["artefact"] = title
                game_data["text"] = text[0] if (len(text)>0 and text[0] != 'nan') else "-"
                game_data["session_id"] = session_id
                game_data["date"] = date[0][:10]
                game_data["emotions"] = emo_text if (len(emo_text)>0) else "-"
                #user
                #hashtag
                #accepted as recommendation
                game_data_list.append(game_data)
        return game_data_list

    gamgame_data = load_gamgame_data(data)

    @st.cache
    def load_emotion_data(data):
        ids_titles = { artefact["ID"]: artefact["title"] for artefact in data }
        emotion_data = []
        key = 	"f6b5743b-220c-4802-8163-7c9de0d6c56d"

        source = requests.get('https://api2.mksmart.org/browse/f1f1018c-6e72-4e95-953e-889d9ae0c914', auth=HTTPBasicAuth(key, key)).json()
        g = ConjunctiveGraph()
        g.parse(data=json.dumps(source["results"][0]),format='json-ld')

        insta = requests.get('https://api2.mksmart.org/browse/a098187d-e5e0-4be8-9961-4e92918cf32a', auth=HTTPBasicAuth(key, key)).json()
        i = ConjunctiveGraph()
        i.parse(data=json.dumps(insta["results"][0]),format='json-ld')

        tweet = requests.get('https://api2.mksmart.org/browse/74270a7b-d9f6-4b15-b7dc-4246505cb409', auth=HTTPBasicAuth(key, key)).json()
        t = ConjunctiveGraph()
        t.parse(data=json.dumps(tweet["results"][0]),format='json-ld')


        gams = requests.get('https://api2.mksmart.org/browse/2c4570bb-c916-4544-9dbd-9831b8bbb246', auth=HTTPBasicAuth(key, key)).json()
        ga = ConjunctiveGraph()
        ga.parse(data=json.dumps(gams["results"][0]),format='json-ld')


        curator_emotions = g.query(
            """
            PREFIX arco: <https://w3id.org/arco/ontology/arco/>
            PREFIX arco-cd: <https://w3id.org/arco/ontology/context-description/>
            PREFIX emotion: <https://w3id.org/spice/SON/emotion/>
            SELECT DISTINCT ?title ?ID ?emotion (COUNT(?emotion_iri) as ?count) ?role
            WHERE {
                BIND("curator" as ?role)
                  ?artefact arco:uniqueIdentifier ?ID ;
                            arco-cd:title ?title ;
                            emotion:triggers ?emotion_iri .
                  ?emotion_iri a ?emotion .
               }
            GROUP BY ?artefact ?title ?ID ?emotion ?count
            """)

        q = prepareQuery(
        """
        PREFIX arco: <https://w3id.org/arco/ontology/arco/>
        PREFIX arco-cd: <https://w3id.org/arco/ontology/context-description/>
        PREFIX emotion: <https://w3id.org/spice/SON/emotion/>
        PREFIX semiotics: <http://ontologydesignpatterns.org/cp/owl/semiotics.owl#>
        PREFIX earmark: <http://www.essepuntato.it/2008/12/earmark#>
        SELECT DISTINCT ?ID ?emotion (COUNT(?emotion_iri) as ?count)
        WHERE {
              ?ID emotion:triggers ?emotion_iri .
              ?emotion_iri a ?emotion .
              ?stmt semiotics:denotes ?emotion_iri;
                    earmark:refersTo ?post .
           }
        GROUP BY ?ID ?emotion ?count
        """
        )

        insta_emotions = i.query(q)
        tweet_emotions = t.query(q)
        gams_emotions = ga.query(q)

        for row in curator_emotions:
            r = {"title": str(row["title"]), "ID": str(row["ID"]), "emotion": str(row["emotion"].split("/")[-1]), "count": int(row["count"]), "role":"curator"}
            emotion_data.append(r)



        for row in insta_emotions:
            ins = {"title": ids_titles[str(row["ID"].split("/")[-1]) ] ,
                    "ID": str(row["ID"].split("/")[-1]) ,
                    "emotion": str(row["emotion"].split("/")[-1]),
                    "count": int(row["count"]), "role":"instagram"}
            emotion_data.append(ins)

        for row in tweet_emotions:
            ins = {"title": ids_titles[str(row["ID"].split("/")[-1]) ] ,
                    "ID": str(row["ID"].split("/")[-1]) ,
                    "emotion": str(row["emotion"].split("/")[-1]),
                    "count": int(row["count"]), "role":"twitter"}
            emotion_data.append(ins)

        for row in gams_emotions:
            gae = {"title": ids_titles[str(row["ID"].split("/")[-1]) ] ,
                    "ID": str(row["ID"].split("/")[-1]) ,
                    "emotion": str(row["emotion"].split("/")[-1]),
                    "count": int(row["count"]), "role":"gam user"}
            emotion_data.append(gae)

        return emotion_data

    emotion_data = load_emotion_data(data)

    return data, twitter_data, instagram_data, gamgame_data , emotion_data

def show_must_go_on():

    data, twitter_data, instagram_data, gamgame_data , emotion_data = parse_data()

    ###############################
    ##### DASHBOARD web app #######
    ###############################

    # style
    st.markdown(
        """
        <style>

        .css-hi6a2p {max-width: 1000px;}
        </style>
        """,
        unsafe_allow_html=True
    )

    # sidebar
    museums = st.sidebar.selectbox(
        'Choose a museum',
         ['GAM Turin'])

    events = st.sidebar.selectbox(
        'Choose an event',
         ['All','Instagram','Twitter','GAMgame','GAMgame alternative'])

    data = pd.DataFrame.from_dict(data)
    emotion_data = pd.DataFrame.from_dict(emotion_data)
    list_title = (data["title"] + ', ' + data["author"]).astype(str).tolist()
    list_title.sort()
    list_title.insert(0, 'all artefacts')
    artefacts = st.sidebar.selectbox(
        'Choose an artefact', list_title)

    # main content
    st.title('Citizen curation activities dashboard')
    st.write('**'+events+'** activities related to **'+artefacts+'** from the **'+museums+'** museum.')

    ###############################
    # Overview distribution chart #
    ###############################

    ## prepare data
    data = data.fillna("")
    idata = data.filter(['title','twitter','instagram','gam_sessions'], axis=1)
    idata = idata.fillna(0)

    # twitter time series
    tmp = defaultdict(list)
    for item in twitter_data:
        tmp[item['date']].append(item['artefact'])

    twitter_data_time = [{"date":k, "value":len(v)} for k,v in tmp.items()]
    twitter_data_time.sort(key=lambda x:x['date'][:7])
    twitter_data_time_simple = []
    for k,v in groupby(twitter_data_time,key=lambda x:x['date'][:7]):
        twitter_data_time_simple.append({'date':k+'-01','value':sum(int(d['value']) for d in v),'platform':'twitter'})

    # instagram time series
    inst = defaultdict(list)
    for item in instagram_data:
        inst[item['date']].append(item['artefact'])
    instagram_data_time = [{"date":k, "value":len(v)} for k,v in inst.items()]
    instagram_data_time.sort(key=lambda x:x['date'][:7])
    instagram_data_time_simple = []
    for k,v in groupby(instagram_data_time,key=lambda x:x['date'][:7]):
        instagram_data_time_simple.append({'date':k+'-01','value':sum(int(d['value']) for d in v),'platform':'instagram'})

    # gamgame time series
    gg = defaultdict(list)
    for item in gamgame_data:
        gg[item['date']].append(item['artefact'])
    gamgame_data_time = [{"date":k, "value":len(v)} for k,v in gg.items()]
    gamgame_data_time.sort(key=lambda x:x['date'][:7])
    gamgame_data_time_simple = []
    for k,v in groupby(gamgame_data_time,key=lambda x:x['date'][:7]):
        gamgame_data_time_simple.append({'date':k+'-01','value':sum(int(d['value']) for d in v),'platform':'gamgame'})

    artefact_tw = []
    for date, art_list in tmp.items():
        art_list_set = set(art_list)
        for art in art_list_set:
            artefact_tw.append({ "date":date, "platform":"twitter", "artefact":art, "count":art_list.count(art) } )
    artefact_inst = []
    for date, art_list in inst.items():
        art_list_set = set(art_list)
        for art in art_list_set:
            artefact_inst.append({ "date":date, "platform":"instagram", "artefact":art, "count":art_list.count(art) } )
    artefact_gg = []
    for date, art_list in gg.items():
        art_list_set = set(art_list)
        for art in art_list_set:
            artefact_gg.append({ "date":date, "platform":"GAMgame", "artefact":art, "count":art_list.count(art) } )

    artefacts_timeseries = pd.concat([ pd.DataFrame(artefact_tw), pd.DataFrame(artefact_inst), pd.DataFrame(artefact_gg)])


    # if an artefact is selected
    if artefacts != 'all artefacts':
        art = artefacts.split(',')[0]

        ################
        # curators' data
        ################

        img = data.loc[ data["title"] == art]["image"].item()
        loc_img = img[0].split('/')[-1]

        if len(img) != 0:
            local_img = requests.get("https://raw.githubusercontent.com/marilenadaquino/spiceboard/main/demonstrator/GAM_test_catalogue_images/""+loc_img)
            if local_img.status_code == 200:
                #if os.path.isfile('GAM_test_catalogue_images/'+loc_img):
                #st.image('GAM_test_catalogue_images/'+loc_img)
                st.image(local_img)
            else:
                st.image(img)
        else:
            st.write("**no image available"+img)

        st.subheader('What curators say about **'+artefacts.split(',')[0]+'**')
        col_img , col_desc = st.beta_columns((1.4,1))
        with col_img:
            desc = data.loc[data["title"] == art]["description"].item()
            st.write("**Description**: "+desc)
        with col_desc:
            author = data.loc[ data["title"] == art]["author"].item()
            loc_id = data.loc[data["title"] == art]["ID"].item()
            actions = data.loc[data["title"] == art]["actions"].item()
            entities = data.loc[data["title"] == art]["entities"].item()
            feelings = data.loc[data["title"] == art]["emotions"].item()
            emotions = data.loc[data["title"] == art]["annotated_emotions"].item()

            if len(actions) > 0:
                st.write("**Represented actions**: `"+"`, `".join(actions)+"`" )
            if entities:
                st.write("**Represented entities**: `"+"`, `".join(entities)+"`" )

            if len(feelings) > 0:
                feelings = [el for el in feelings if isinstance(el,str)]
                st.write("**Suggested feelings**: `"+"`, `".join(feelings)+"`" )
            if len(emotions) > 0:
                emotions = list(set([el for el in emotions if isinstance(el,str)]))
                st.write("**Suggested emotions**: `"+"`, `".join(emotions)+"`" )

        # prepare data for the charts
        idata = idata.set_index(['title'])
        filtered_data = idata.loc[art]
        filtered_twitter_data = [tweet for tweet in twitter_data if tweet["artefact"] == art]
        filtered_instagram_data = [tweet for tweet in instagram_data if tweet["artefact"] == art]
        filtered_gamgame_data = [art_ for art_ in gamgame_data if art_["artefact"] == art]
        st.markdown("<hr/>", unsafe_allow_html=True)
        # distribution
        st.subheader('User interactions with **'+artefacts+'**')
        st.bar_chart(filtered_data)

        # artefact timeline
        filtered_artefacts_timeseries = artefacts_timeseries[artefacts_timeseries['artefact'] == artefacts.split(',')[0]]
        if events == 'Twitter':
            filtered_artefacts_timeseries = filtered_artefacts_timeseries[filtered_artefacts_timeseries['platform'] == 'twitter']
        if events == 'Instagram':
            filtered_artefacts_timeseries = filtered_artefacts_timeseries[filtered_artefacts_timeseries['platform'] == 'instagram']
        if events == 'GAMgame':
            filtered_artefacts_timeseries = filtered_artefacts_timeseries[filtered_artefacts_timeseries['platform'] == 'gamgame']

        st.markdown("<hr/>", unsafe_allow_html=True)
        st.subheader('**'+events+'** activities related to **'+artefacts+'** over time')
        artefact_time_chart = alt.Chart(filtered_artefacts_timeseries).mark_circle(opacity=1).encode(
            x='yearmonth(date):T',
            y='count:Q',
            size='count:Q',
            color='platform:N',
            tooltip=['date:T', 'count', 'platform'],
        ).properties(width=1000)
        st.write(artefact_time_chart)

        st.markdown("<hr/>", unsafe_allow_html=True)
        # emotions
        filtered_emotions = emotion_data[emotion_data["title"] == art]
        st.subheader('**'+events+'** emotional responses related to **'+artefacts+'**')
        st.write("Overview of emotions (by lemmas)")
        if events == 'All' or events == 'GAM game alternative':
            chart_emo = alt.Chart(filtered_emotions).mark_bar().encode(
                #column='role:N',
                x='count:Q',
                y='role:N',
                color='emotion:N',
                tooltip=['emotion', 'count'],
                order=alt.Order('count', sort='descending')
            ).properties(width=650)
            st.write(chart_emo)
        else:
            if events == 'Twitter':
                filtered_emotions = filtered_emotions[filtered_emotions["role"] == "twitter"]
            if events == 'Instagram':
                filtered_emotions = filtered_emotions[filtered_emotions["role"] == "instagram"]
            if events == 'GAM game':
                filtered_emotions = filtered_emotions[filtered_emotions["role"] == "gam user"]
            chart_emo = alt.Chart(filtered_emotions).mark_bar().encode(
                #column='role:N',
                x='count:Q',
                y='emotion:N',
                color='emotion:N',
                tooltip=['emotion', 'count'],
                order=alt.Order('count', sort='descending')
            ).properties(width=450)
            st.write(chart_emo)

    else: # show all artefacts
        idata = pd.melt(idata,id_vars=['title'], value_vars=['twitter','instagram','gam_sessions'],var_name='platform', value_name='count')
        filtered_data = idata
        filtered_twitter_data = twitter_data
        filtered_instagram_data = instagram_data
        filtered_gamgame_data = gamgame_data
        # time series
        twitter_data_time_pd = pd.DataFrame(twitter_data_time_simple)
        instagram_data_time_pd = pd.DataFrame(instagram_data_time_simple)
        gamgame_data_time_pd = pd.DataFrame(gamgame_data_time_simple)
        timeseries = pd.concat([twitter_data_time_pd, instagram_data_time_pd, gamgame_data_time_pd])
        filtered_timeseries = timeseries
        filtered_emotions = emotion_data

        # sidebar filters
        if events == 'All' or events == 'GAMgame alternative':
            filtered_data = filtered_data
            filtered_timeseries = filtered_timeseries
            filtered_emotions = filtered_emotions
        if events == 'Twitter':
            filtered_data = filtered_data[filtered_data['platform'] == 'twitter']
            filtered_timeseries = filtered_timeseries[filtered_timeseries['platform'] == 'twitter']
            filtered_emotions = filtered_emotions[filtered_emotions['role'] == 'twitter']
        if events == 'Instagram':
            filtered_data = filtered_data[filtered_data['platform'] == 'instagram']
            filtered_timeseries = filtered_timeseries[filtered_timeseries['platform'] == 'instagram']
            filtered_emotions = filtered_emotions[filtered_emotions['role'] == 'instagram']
        if events == 'GAMgame':
            filtered_data = filtered_data[filtered_data['platform'] == 'gam_sessions']
            filtered_timeseries = filtered_timeseries[filtered_timeseries['platform'] == 'gamgame']
            filtered_emotions = filtered_emotions[filtered_emotions['role'] == 'gam user']


        # time series
        st.subheader('**'+events+'** activities related to **'+artefacts+'** over time')
        time_chart = alt.Chart(filtered_timeseries).mark_area(opacity=0.7).encode(
            x='yearmonth(date):T',
            y='value:Q',
            color='platform:N',
            tooltip=['date:T', 'value', 'platform'],
        ).properties(width=1000)
        st.write(time_chart)

        st.markdown("<hr/>", unsafe_allow_html=True)

        ## plot distribution by artefact
        st.subheader('Distribution of **'+events+'** activities related to **'+artefacts+'**')
        count_filter = st.slider('Filter by number of interactions', 1, 1000, 1000)
        filtered_data = filtered_data[filtered_data['count'] <= count_filter]
        chart_v1 = alt.Chart(filtered_data).mark_bar().encode(
            x='title',
            y='count',
            color='platform',
            tooltip=['title', 'count', 'platform'],
            order=alt.Order('sum(count)', sort='descending')
        ).properties(height=600)
        st.write(chart_v1)

        st.markdown("<hr/>", unsafe_allow_html=True)


        st.subheader('**'+events+'** emotional responses to **'+artefacts+'**')

        chart_emo = alt.Chart(filtered_emotions).mark_bar().encode(
            #column='role:N',
            y='count:Q',
            x='title:N',
            color='emotion:N',
            tooltip=['emotion', 'count'],
            order=alt.Order('count', sort='descending')
        ).properties(height=600)
        st.write(chart_emo)

    ###########
    # Stories #
    ###########
    st.markdown("<hr/>", unsafe_allow_html=True)
    st.subheader('Read **'+events+'** user stories about **'+artefacts+'**')
    col1, col2, col3 = st.beta_columns((1.7,  1.7,  1.7))
    filtered_twitter_data = sorted(filtered_twitter_data, key=lambda k: k['date'], reverse=True)
    filtered_instagram_data = sorted(filtered_instagram_data, key=lambda k: k['date'], reverse=True)

    if events == 'All' or events == 'GAMgame alternative' or events == 'Twitter':
        if events == 'Twitter':
            col1, col2, col3 = st.beta_columns((1.7,  .1,  .1))
        with col1:
            st.header("Twitter ("+str(len(filtered_twitter_data))+")")
            count_filter = st.slider('Filter tweets:', 1, len(filtered_twitter_data), 10)
            for tweet in filtered_twitter_data[:count_filter]:
                st.markdown("<hr/>", unsafe_allow_html=True)
                st.write('**about: '+tweet["artefact"]+'**, '+tweet["date"][:10])
                st.write(tweet["txt"].replace("\\n","\n").replace("\\xa0"," "))
                st.image(tweet["img"])

    if events == 'All' or events == 'GAMgame alternative' or events == 'Instagram':
        if events == 'Instagram':
            col2, col1,  col3 = st.beta_columns((1.7,  .1,  .1))
        with col2:
            st.header("Instagram ("+str(len(filtered_instagram_data))+")")
            count_filter = st.slider('Filter posts:', 1, len(filtered_instagram_data), 10)
            for post in filtered_instagram_data[:count_filter]:
                st.markdown("<hr/>", unsafe_allow_html=True)
                st.write('**about: '+post["artefact"]+'**, '+post["date"][:10])
                st.markdown(post["txt"].replace("\\n","\n").replace("\\xa0"," "))
                if post["img"] and post["img"] != '':
                    st.image(post["img"])

    emoji_html = {
        "paura": ":scream:",
        "gioia":":smiley:",
        "scettico":":confused:",
        "tristezza":":cry:",
        "serenità":":relieved:",
        "amore":":heart_eyes:",
        "disgusto":"&#;" }

    if events == 'All' or events == 'GAMgame alternative' or events == 'GAMgame':
        if events == 'GAMgame':
            col3, col1, col2 = st.beta_columns((1.7,  .1,  .1))
        with col3:
            st.header("GAM game ("+str(len(filtered_gamgame_data))+")")
            count_filter = st.slider('Filter stories:', 1, len(filtered_gamgame_data), 10)
            for story in filtered_gamgame_data[:count_filter]:
                st.markdown("<hr/>", unsafe_allow_html=True)
                st.write("**about: "+story["artefact"]+'**, '+story["date"][:10])
                st.write("**said**: "+story["text"])
                emos = ", ".join([emoji_html[emo.strip()] if emo in emoji_html else emo for emot in story["emotions"] for emo in emot.split()])
                if len(emos):
                    st.markdown("**emoji**: "+emos, unsafe_allow_html=True)


###############################
##### SIMPLE AUTHENTICATION ###
###############################

# authenticated = False
# pw_container =  st.empty()
# state_password = None
# if state_password is None:
#     state_password = pw_container.text_input("Enter the pass phrase", type="password")
# if state_password == st.secrets["passphrase"]:
#     pw_container.empty()
#     show_must_go_on()
from SessionState import get

session_state = get(password='')

if session_state.password != st.secrets["passphrase"]:
    pwd_placeholder = st.sidebar.empty()
    pwd = pwd_placeholder.text_input("passphrase:", value="", type="password")
    session_state.password = pwd
    if session_state.password == st.secrets["passphrase"]:
        pwd_placeholder.empty()
        show_must_go_on()
    elif session_state.password != '':
        st.error("the passphrase you entered is incorrect")
else:
    show_must_go_on()
#show_must_go_on()
