import json, datetime, re, time
import pyDataverse.api as pyd
from corere.main import models as m
from corere.main import git as g
from django.conf import settings

#Goes to the dataset for the manuscript, grabs the citation information and updates the manuscript
def update_citation_data(manuscript):
    # native_api = pyd.NativeApi(manuscript.dataverse_installation.url, api_token=manuscript.dataverse_installation.api_token)
    # native_dataset_json = native_api.get_dataset(manuscript.dataverse_fetched_doi).json()['data']    
    #print(native_dataset_json)

    search_api = pyd.SearchApi(manuscript.dataverse_installation.url, api_token=manuscript.dataverse_installation.api_token)
    search_dataset_json = search_api.search('dsPersistentId:"'+manuscript.dataverse_fetched_doi+'"',auth=True).json()['data']
    #print(search_dataset_json)
    try:
        #TODO: Eventually we may need to grab all the publications, but for now we assume there will only be one
        manuscript.dataverse_fetched_article_citation = search_dataset_json['items'][0]['publications'][0]['citation'] + " " + search_dataset_json['items'][0]['publications'][0]['url']
    except Exception:
        pass #We are ok with publications not existing

    try:
        manuscript.dataverse_fetched_data_citation = re.sub('<[^<]+?>', '', search_dataset_json['items'][0]['citationHtml']) #re.sub removes link html
    except Exception:
        raise ValueError("Unable to get 'citationHtml' from dataset json.")

    try:
        manuscript.dataverse_fetched_publish_date = datetime.datetime.strptime(search_dataset_json['items'][0]['published_at'], "%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        raise ValueError("Unable to get 'published_at' from dataset json. Maybe the dataset has not been published.")

    #manuscript.save()


#Note: this uploads the data for the approved submission
def upload_manuscript_data_to_dataverse(manuscript):
    native_api = pyd.NativeApi(manuscript.dataverse_installation.url, api_token=manuscript.dataverse_installation.api_token)
    dataset_json = build_dataset_json(manuscript)

    create_dataset_response = native_api.create_dataset(manuscript.dataverse_parent, dataset_json, pid=None, publish=False, auth=True).json()
    #print(create_dataset_response) #TODO: I need to handle erroring here better, I think some dataverses have stricter field requirements?

    dataset_pid = create_dataset_response['data']['persistentId'] #dataverse is either the alias or the id

    submission = manuscript.get_latest_submission()
    submission_files = submission.submission_files.all().order_by('path','name')
    files_root_path = g.get_submission_files_path(manuscript)

    for git_file in submission_files:    
        lock_response = native_api.get_dataset_lock(dataset_pid).json()
        while lock_response['data']: #If locked (usually tabular ingest), wait
            #print("LOCKED")
            time.sleep(1)
            lock_response = native_api.get_dataset_lock(dataset_pid).json()

        file_response = native_api.upload_datafile(dataset_pid, files_root_path + git_file.full_path, json_str=None, is_pid=True)
        # print(git_file.full_path)
        # print(file_response.json())
        if file_response.json()['status'] == 'OK':
            # print(file_response.json()['data'])
            file_id = file_response.json()['data']['files'][0]['dataFile']['id']
            native_api.redetect_file_type(file_id) #If we don't redetect the file type dataverse seems to think it is text always
        else:
            raise Exception("Exception from dataverse during upload: " + file_response.json()['message']) #TODO: Handle this better?

    manuscript.dataverse_fetched_doi = dataset_pid
    manuscript.dataverse_fetched_article_citation = ""
    manuscript.dataverse_fetched_data_citation = ""
    manuscript.dataverse_fetched_publish_date = None
    # manuscript.dataverse_upload_noop()
    #manuscript.save()

# Converts manuscript fields and hardcoded data to a dictionary that is then converted to json
def build_dataset_json(manuscript):
    # The approach I've taken for this is to take the whole dataset-create-new-all-default-fields.json from https://guides.dataverse.org/en/latest/api/native-api.html#
    # and just comment out the unused parts. It takes up a lot of space but it means we can easily enable more as we expand.

    # It may be possible to build these dictionary-lists inline using comprehension (see https://stackoverflow.com/questions/19121722/), 
    # but it seems less crazy to just do it beforehand and append in the sections

    citation_authors_dict_list = []
    for author in manuscript.manuscript_authors.all().order_by('id'):
        if author.identifier_scheme:
            author_dict = {
                            "authorName": {
                                "typeName": "authorName",
                                "multiple": False,
                                "typeClass": "primitive",
                                "value": author.last_name + ", " + author.first_name #"LastAuthor1, FirstAuthor1"
                            },
                            # "authorAffiliation": {
                            #     "typeName": "authorAffiliation",
                            #     "multiple": False,
                            #     "typeClass": "primitive",
                            #     "value": "AuthorAffiliation1"
                            # },
                            "authorIdentifierScheme": {
                                "typeName": "authorIdentifierScheme",
                                "multiple": False,
                                "typeClass": "controlledVocabulary",
                                "value": author.identifier_scheme #"ORCID"
                            },
                            "authorIdentifier": {
                                "typeName": "authorIdentifier",
                                "multiple": False,
                                "typeClass": "primitive",
                                "value": author.identifier #"AuthorIdentifier1"
                            }
                        }
        else:
            author_dict = {
                            "authorName": {
                                "typeName": "authorName",
                                "multiple": False,
                                "typeClass": "primitive",
                                "value": author.last_name + ", " + author.first_name #"LastAuthor1, FirstAuthor1"
                            }
                        }
        citation_authors_dict_list.append(author_dict)

    keywords_dict_list = []
    for keyword in manuscript.manuscript_keywords.all().order_by('id'):
        keyword_dict = {
                            "keywordValue": {
                                "typeName": "keywordValue",
                                "multiple": False,
                                "typeClass": "primitive",
                                "value": keyword.text
                            },
                            # "keywordVocabulary": {
                            #     "typeName": "keywordVocabulary",
                            #     "multiple": False,
                            #     "typeClass": "primitive",
                            #     "value": "KeywordVocabulary1"
                            # },
                            # "keywordVocabularyURI": {
                            #     "typeName": "keywordVocabularyURI",
                            #     "multiple": False,
                            #     "typeClass": "primitive",
                            #     "value": "http://KeywordVocabularyURL1.org"
                            # }
                        }
        keywords_dict_list.append(keyword_dict)

    data_sources_array = []
    for data_source in manuscript.manuscript_data_sources.all().order_by('id'):
        data_sources_array.append(data_source.text)

    full_dataset_dict = {
        "datasetVersion": {
            # "license": {
            #     "name": "CC0 1.0",
            #     "uri": "http://creativecommons.org/publicdomain/zero/1.0"
            # },
            "metadataBlocks": {
                "citation": {
                    "displayName": "Citation Metadata",
                    "fields": [
                        {
                            "typeName": "title",
                            "multiple": False,
                            "typeClass": "primitive",
                            "value": manuscript.pub_name
                        },
                        # {
                        #     "typeName": "subtitle",
                        #     "multiple": False,
                        #     "typeClass": "primitive",
                        #     "value": "Subtitle"
                        # },
                        # {
                        #     "typeName": "alternativeTitle",
                        #     "multiple": False,
                        #     "typeClass": "primitive",
                        #     "value": "Alternative Title"
                        # },
                        # {
                        #     "typeName": "alternativeURL",
                        #     "multiple": False,
                        #     "typeClass": "primitive",
                        #     "value": "http://AlternativeURL.org"
                        # },
                        # {
                        #     "typeName": "otherId",
                        #     "multiple": True,
                        #     "typeClass": "compound",
                        #     "value": [
                        #         {
                        #             "otherIdAgency": {
                        #                 "typeName": "otherIdAgency",
                        #                 "multiple": False,
                        #                 "typeClass": "primitive",
                        #                 "value": "OtherIDAgency1"
                        #             },
                        #             "otherIdValue": {
                        #                 "typeName": "otherIdValue",
                        #                 "multiple": False,
                        #                 "typeClass": "primitive",
                        #                 "value": "OtherIDIdentifier1"
                        #             }
                        #         },
                        #         {
                        #             "otherIdAgency": {
                        #                 "typeName": "otherIdAgency",
                        #                 "multiple": False,
                        #                 "typeClass": "primitive",
                        #                 "value": "OtherIDAgency2"
                        #             },
                        #             "otherIdValue": {
                        #                 "typeName": "otherIdValue",
                        #                 "multiple": False,
                        #                 "typeClass": "primitive",
                        #                 "value": "OtherIDIdentifier2"
                        #             }
                        #         }
                        #     ]
                        # },
                        {
                            "typeName": "author",
                            "multiple": True,
                            "typeClass": "compound",
                            "value": citation_authors_dict_list
                                # [
                                # {
                                #     "authorName": {
                                #         "typeName": "authorName",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "LastAuthor1, FirstAuthor1"
                                #     },
                                #     "authorAffiliation": {
                                #         "typeName": "authorAffiliation",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "AuthorAffiliation1"
                                #     },
                                #     "authorIdentifierScheme": {
                                #         "typeName": "authorIdentifierScheme",
                                #         "multiple": False,
                                #         "typeClass": "controlledVocabulary",
                                #         "value": "ORCID"
                                #     },
                                #     "authorIdentifier": {
                                #         "typeName": "authorIdentifier",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "AuthorIdentifier1"
                                #     }
                                # },
                                # {
                                #     "authorName": {
                                #         "typeName": "authorName",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "LastAuthor2, FirstAuthor2"
                                #     },
                                #     "authorAffiliation": {
                                #         "typeName": "authorAffiliation",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "AuthorAffiliation2"
                                #     },
                                #     "authorIdentifierScheme": {
                                #         "typeName": "authorIdentifierScheme",
                                #         "multiple": False,
                                #         "typeClass": "controlledVocabulary",
                                #         "value": "ISNI"
                                #     },
                                #     "authorIdentifier": {
                                #         "typeName": "authorIdentifier",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "AuthorIdentifier2"
                                #     }
                                # }
                                # ]
                        },
                        {
                            "typeName": "datasetContact",
                            "multiple": True,
                            "typeClass": "compound",
                            "value": [
                                { #We only collect one contact currently
                                    "datasetContactName": {
                                        "typeName": "datasetContactName",
                                        "multiple": False,
                                        "typeClass": "primitive",
                                        "value": manuscript.contact_last_name + ', ' + manuscript.contact_first_name
                                    },
                                    # "datasetContactAffiliation": {
                                    #     "typeName": "datasetContactAffiliation",
                                    #     "multiple": False,
                                    #     "typeClass": "primitive",
                                    #     "value": "ContactAffiliation1"
                                    # },
                                    "datasetContactEmail": {
                                        "typeName": "datasetContactEmail",
                                        "multiple": False,
                                        "typeClass": "primitive",
                                        "value": manuscript.contact_email   
                                    }
                                },

                                # {
                                #     "datasetContactName": {
                                #         "typeName": "datasetContactName",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "LastContact1, FirstContact1"
                                #     },
                                #     "datasetContactAffiliation": {
                                #         "typeName": "datasetContactAffiliation",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "ContactAffiliation1"
                                #     },
                                #     "datasetContactEmail": {
                                #         "typeName": "datasetContactEmail",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "ContactEmail1@mailinator.com"
                                #     }
                                # },
                                # {
                                #     "datasetContactName": {
                                #         "typeName": "datasetContactName",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "LastContact2, FirstContact2"
                                #     },
                                #     "datasetContactAffiliation": {
                                #         "typeName": "datasetContactAffiliation",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "ContactAffiliation2"
                                #     },
                                #     "datasetContactEmail": {
                                #         "typeName": "datasetContactEmail",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "ContactEmail2@mailinator.com"
                                #     }
                                # }
                            ]
                        },
                        {
                            "typeName": "dsDescription",
                            "multiple": True,
                            "typeClass": "compound",
                            "value": [
                                {
                                    "dsDescriptionValue": {
                                        "typeName": "dsDescriptionValue",
                                        "multiple": False,
                                        "typeClass": "primitive",
                                        "value": manuscript.description
                                    },
                            #TODO: We may need this date.
                                    # "dsDescriptionDate": {
                                    #     "typeName": "dsDescriptionDate",
                                    #     "multiple": False,
                                    #     "typeClass": "primitive",
                                    #     "value": "1000-01-01"
                                    # }

                                },
                                # {
                                #     "dsDescriptionValue": {
                                #         "typeName": "dsDescriptionValue",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "DescriptionText2"
                                #     },
                                #     "dsDescriptionDate": {
                                #         "typeName": "dsDescriptionDate",
                                #         "multiple": False,
                                #         "typeClass": "primitive",
                                #         "value": "1000-02-02"
                                #     }
                                # }
                            ]
                        },
                        {
                            "typeName": "subject",
                            "multiple": True,
                            "typeClass": "controlledVocabulary",
                            "value": [ manuscript.get_subject_display()
                                # "Agricultural Sciences",
                                # "Business and Management",
                                # "Engineering",
                                # "Law"
                            ]
                        },
                        {
                            "typeName": "keyword",
                            "multiple": True,
                            "typeClass": "compound",
                            "value": keywords_dict_list
                    # [
                    #             {
                    #                 "keywordValue": {
                    #                     "typeName": "keywordValue",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "KeywordTerm1"
                    #                 },
                    #                 "keywordVocabulary": {
                    #                     "typeName": "keywordVocabulary",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "KeywordVocabulary1"
                    #                 },
                    #                 "keywordVocabularyURI": {
                    #                     "typeName": "keywordVocabularyURI",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://KeywordVocabularyURL1.org"
                    #                 }
                    #             },
                    #             {
                    #                 "keywordValue": {
                    #                     "typeName": "keywordValue",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "KeywordTerm2"
                    #                 },
                    #                 "keywordVocabulary": {
                    #                     "typeName": "keywordVocabulary",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "KeywordVocabulary2"
                    #                 },
                    #                 "keywordVocabularyURI": {
                    #                     "typeName": "keywordVocabularyURI",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://KeywordVocabularyURL2.org"
                    #                 }
                    #             }
                    #         ]
                        },
                    #     {
                    #         "typeName": "topicClassification",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "topicClassValue": {
                    #                     "typeName": "topicClassValue",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "Topic Classification Term1"
                    #                 },
                    #                 "topicClassVocab": {
                    #                     "typeName": "topicClassVocab",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "Topic Classification Vocab1"
                    #                 },
                    #                 "topicClassVocabURI": {
                    #                     "typeName": "topicClassVocabURI",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "https://TopicClassificationURL1.com"
                    #                 }
                    #             },
                    #             {
                    #                 "topicClassValue": {
                    #                     "typeName": "topicClassValue",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "Topic Classification Term2"
                    #                 },
                    #                 "topicClassVocab": {
                    #                     "typeName": "topicClassVocab",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "Topic Classification Vocab2"
                    #                 },
                    #                 "topicClassVocabURI": {
                    #                     "typeName": "topicClassVocabURI",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "https://TopicClassificationURL2.com"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "publication",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "publicationCitation": {
                    #                     "typeName": "publicationCitation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "RelatedPublicationCitation1"
                    #                 },
                    #                 "publicationIDType": {
                    #                     "typeName": "publicationIDType",
                    #                     "multiple": False,
                    #                     "typeClass": "controlledVocabulary",
                    #                     "value": "ark"
                    #                 },
                    #                 "publicationIDNumber": {
                    #                     "typeName": "publicationIDNumber",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "RelatedPublicationIDNumber1"
                    #                 },
                    #                 "publicationURL": {
                    #                     "typeName": "publicationURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://RelatedPublicationURL1.org"
                    #                 }
                    #             },
                    #             {
                    #                 "publicationCitation": {
                    #                     "typeName": "publicationCitation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "RelatedPublicationCitation2"
                    #                 },
                    #                 "publicationIDType": {
                    #                     "typeName": "publicationIDType",
                    #                     "multiple": False,
                    #                     "typeClass": "controlledVocabulary",
                    #                     "value": "arXiv"
                    #                 },
                    #                 "publicationIDNumber": {
                    #                     "typeName": "publicationIDNumber",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "RelatedPublicationIDNumber2"
                    #                 },
                    #                 "publicationURL": {
                    #                     "typeName": "publicationURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://RelatedPublicationURL2.org"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "notesText",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "Notes1"
                    #     },
                    #     {
                    #         "typeName": "language",
                    #         "multiple": True,
                    #         "typeClass": "controlledVocabulary",
                    #         "value": [
                    #             "Abkhaz",
                    #             "Afar"
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "producer",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "producerName": {
                    #                     "typeName": "producerName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "LastProducer1, FirstProducer1"
                    #                 },
                    #                 "producerAffiliation": {
                    #                     "typeName": "producerAffiliation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "ProducerAffiliation1"
                    #                 },
                    #                 "producerAbbreviation": {
                    #                     "typeName": "producerAbbreviation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "ProducerAbbreviation1"
                    #                 },
                    #                 "producerURL": {
                    #                     "typeName": "producerURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://ProducerURL1.org"
                    #                 },
                    #                 "producerLogoURL": {
                    #                     "typeName": "producerLogoURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://ProducerLogoURL1.org"
                    #                 }
                    #             },
                    #             {
                    #                 "producerName": {
                    #                     "typeName": "producerName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "LastProducer2, FirstProducer2"
                    #                 },
                    #                 "producerAffiliation": {
                    #                     "typeName": "producerAffiliation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "ProducerAffiliation2"
                    #                 },
                    #                 "producerAbbreviation": {
                    #                     "typeName": "producerAbbreviation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "ProducerAbbreviation2"
                    #                 },
                    #                 "producerURL": {
                    #                     "typeName": "producerURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://ProducerURL2.org"
                    #                 },
                    #                 "producerLogoURL": {
                    #                     "typeName": "producerLogoURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://ProducerLogoURL2.org"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "productionDate",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "1003-01-01"
                    #     },
                    #     {
                    #         "typeName": "productionPlace",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "ProductionPlace"
                    #     },
                    #     {
                    #         "typeName": "contributor",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "contributorType": {
                    #                     "typeName": "contributorType",
                    #                     "multiple": False,
                    #                     "typeClass": "controlledVocabulary",
                    #                     "value": "Data Collector"
                    #                 },
                    #                 "contributorName": {
                    #                     "typeName": "contributorName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "LastContributor1, FirstContributor1"
                    #                 }
                    #             },
                    #             {
                    #                 "contributorType": {
                    #                     "typeName": "contributorType",
                    #                     "multiple": False,
                    #                     "typeClass": "controlledVocabulary",
                    #                     "value": "Data Curator"
                    #                 },
                    #                 "contributorName": {
                    #                     "typeName": "contributorName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "LastContributor2, FirstContributor2"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "grantNumber",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "grantNumberAgency": {
                    #                     "typeName": "grantNumberAgency",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "GrantInformationGrantAgency1"
                    #                 },
                    #                 "grantNumberValue": {
                    #                     "typeName": "grantNumberValue",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "GrantInformationGrantNumber1"
                    #                 }
                    #             },
                    #             {
                    #                 "grantNumberAgency": {
                    #                     "typeName": "grantNumberAgency",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "GrantInformationGrantAgency2"
                    #                 },
                    #                 "grantNumberValue": {
                    #                     "typeName": "grantNumberValue",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "GrantInformationGrantNumber2"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "distributor",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "distributorName": {
                    #                     "typeName": "distributorName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "LastDistributor1, FirstDistributor1"
                    #                 },
                    #                 "distributorAffiliation": {
                    #                     "typeName": "distributorAffiliation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "DistributorAffiliation1"
                    #                 },
                    #                 "distributorAbbreviation": {
                    #                     "typeName": "distributorAbbreviation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "DistributorAbbreviation1"
                    #                 },
                    #                 "distributorURL": {
                    #                     "typeName": "distributorURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://DistributorURL1.org"
                    #                 },
                    #                 "distributorLogoURL": {
                    #                     "typeName": "distributorLogoURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://DistributorLogoURL1.org"
                    #                 }
                    #             },
                    #             {
                    #                 "distributorName": {
                    #                     "typeName": "distributorName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "LastDistributor2, FirstDistributor2"
                    #                 },
                    #                 "distributorAffiliation": {
                    #                     "typeName": "distributorAffiliation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "DistributorAffiliation2"
                    #                 },
                    #                 "distributorAbbreviation": {
                    #                     "typeName": "distributorAbbreviation",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "DistributorAbbreviation2"
                    #                 },
                    #                 "distributorURL": {
                    #                     "typeName": "distributorURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://DistributorURL2.org"
                    #                 },
                    #                 "distributorLogoURL": {
                    #                     "typeName": "distributorLogoURL",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "http://DistributorLogoURL2.org"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "distributionDate",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "1004-01-01"
                    #     },
                    #     {
                    #         "typeName": "depositor",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "LastDepositor, FirstDepositor"
                    #     },
                    #     {
                    #         "typeName": "dateOfDeposit",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "1002-01-01"
                    #     },
                    #     {
                    #         "typeName": "timePeriodCovered",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "timePeriodCoveredStart": {
                    #                     "typeName": "timePeriodCoveredStart",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1005-01-01"
                    #                 },
                    #                 "timePeriodCoveredEnd": {
                    #                     "typeName": "timePeriodCoveredEnd",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1005-01-02"
                    #                 }
                    #             },
                    #             {
                    #                 "timePeriodCoveredStart": {
                    #                     "typeName": "timePeriodCoveredStart",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1005-02-01"
                    #                 },
                    #                 "timePeriodCoveredEnd": {
                    #                     "typeName": "timePeriodCoveredEnd",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1005-02-02"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "dateOfCollection",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "dateOfCollectionStart": {
                    #                     "typeName": "dateOfCollectionStart",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1006-01-01"
                    #                 },
                    #                 "dateOfCollectionEnd": {
                    #                     "typeName": "dateOfCollectionEnd",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1006-01-01"
                    #                 }
                    #             },
                    #             {
                    #                 "dateOfCollectionStart": {
                    #                     "typeName": "dateOfCollectionStart",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1006-02-01"
                    #                 },
                    #                 "dateOfCollectionEnd": {
                    #                     "typeName": "dateOfCollectionEnd",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "1006-02-02"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "kindOfData",
                    #         "multiple": True,
                    #         "typeClass": "primitive",
                    #         "value": [
                    #             "KindOfData1",
                    #             "KindOfData2"
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "series",
                    #         "multiple": False,
                    #         "typeClass": "compound",
                    #         "value": {
                    #             "seriesName": {
                    #                 "typeName": "seriesName",
                    #                 "multiple": False,
                    #                 "typeClass": "primitive",
                    #                 "value": "SeriesName"
                    #             },
                    #             "seriesInformation": {
                    #                 "typeName": "seriesInformation",
                    #                 "multiple": False,
                    #                 "typeClass": "primitive",
                    #                 "value": "SeriesInformation"
                    #             }
                    #         }
                    #     },
                    #     {
                    #         "typeName": "software",
                    #         "multiple": True,
                    #         "typeClass": "compound",
                    #         "value": [
                    #             {
                    #                 "softwareName": {
                    #                     "typeName": "softwareName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "SoftwareName1"
                    #                 },
                    #                 "softwareVersion": {
                    #                     "typeName": "softwareVersion",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "SoftwareVersion1"
                    #                 }
                    #             },
                    #             {
                    #                 "softwareName": {
                    #                     "typeName": "softwareName",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "SoftwareName2"
                    #                 },
                    #                 "softwareVersion": {
                    #                     "typeName": "softwareVersion",
                    #                     "multiple": False,
                    #                     "typeClass": "primitive",
                    #                     "value": "SoftwareVersion2"
                    #                 }
                    #             }
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "relatedMaterial",
                    #         "multiple": True,
                    #         "typeClass": "primitive",
                    #         "value": [
                    #             "RelatedMaterial1",
                    #             "RelatedMaterial2"
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "relatedDatasets",
                    #         "multiple": True,
                    #         "typeClass": "primitive",
                    #         "value": [
                    #             "RelatedDatasets1",
                    #             "RelatedDatasets2"
                    #         ]
                    #     },
                    #     {
                    #         "typeName": "otherReferences",
                    #         "multiple": True,
                    #         "typeClass": "primitive",
                    #         "value": [
                    #             "OtherReferences1",
                    #             "OtherReferences2"
                    #         ]
                    #     },
                        {
                            "typeName": "dataSources",
                            "multiple": True,
                            "typeClass": "primitive",
                            "value": data_sources_array
                        },
                    #     {
                    #         "typeName": "originOfSources",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "OriginOfSources"
                    #     },
                    #     {
                    #         "typeName": "characteristicOfSources",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "CharacteristicOfSourcesNoted"
                    #     },
                    #     {
                    #         "typeName": "accessToSources",
                    #         "multiple": False,
                    #         "typeClass": "primitive",
                    #         "value": "DocumentationAndAccessToSources"
                    #     }

                    ]
                },

                # "geospatial": {
                #     "displayName": "Geospatial Metadata",
                #     "fields": [
                #         {
                #             "typeName": "geographicCoverage",
                #             "multiple": True,
                #             "typeClass": "compound",
                #             "value": [
                #                 {
                #                     "country": {
                #                         "typeName": "country",
                #                         "multiple": False,
                #                         "typeClass": "controlledVocabulary",
                #                         "value": "Afghanistan"
                #                     },
                #                     "state": {
                #                         "typeName": "state",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "GeographicCoverageStateProvince1"
                #                     },
                #                     "city": {
                #                         "typeName": "city",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "GeographicCoverageCity1"
                #                     },
                #                     "otherGeographicCoverage": {
                #                         "typeName": "otherGeographicCoverage",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "GeographicCoverageOther1"
                #                     }
                #                 },
                #                 {
                #                     "country": {
                #                         "typeName": "country",
                #                         "multiple": False,
                #                         "typeClass": "controlledVocabulary",
                #                         "value": "Albania"
                #                     },
                #                     "state": {
                #                         "typeName": "state",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "GeographicCoverageStateProvince2"
                #                     },
                #                     "city": {
                #                         "typeName": "city",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "GeographicCoverageCity2"
                #                     },
                #                     "otherGeographicCoverage": {
                #                         "typeName": "otherGeographicCoverage",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "GeographicCoverageOther2"
                #                     }
                #                 }
                #             ]
                #         },
                #         {
                #             "typeName": "geographicUnit",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "GeographicUnit1",
                #                 "GeographicUnit2"
                #             ]
                #         },
                #         {
                #             "typeName": "geographicBoundingBox",
                #             "multiple": True,
                #             "typeClass": "compound",
                #             "value": [
                #                 {
                #                     "westLongitude": {
                #                         "typeName": "westLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "10"
                #                     },
                #                     "eastLongitude": {
                #                         "typeName": "eastLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "20"
                #                     },
                #                     "northLongitude": {
                #                         "typeName": "northLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "30"
                #                     },
                #                     "southLongitude": {
                #                         "typeName": "southLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "40"
                #                     }
                #                 },
                #                 {
                #                     "westLongitude": {
                #                         "typeName": "westLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "50"
                #                     },
                #                     "eastLongitude": {
                #                         "typeName": "eastLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "60"
                #                     },
                #                     "northLongitude": {
                #                         "typeName": "northLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "70"
                #                     },
                #                     "southLongitude": {
                #                         "typeName": "southLongitude",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "80"
                #                     }
                #                 }
                #             ]
                #         }
                #     ]
                # },
                # "socialscience": {
                #     "displayName": "Social Science and Humanities Metadata",
                #     "fields": [
                #         {
                #             "typeName": "unitOfAnalysis",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "UnitOfAnalysis1",
                #                 "UnitOfAnalysis2"
                #             ]
                #         },
                #         {
                #             "typeName": "universe",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "Universe1",
                #                 "Universe2"
                #             ]
                #         },
                #         {
                #             "typeName": "timeMethod",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "TimeMethod"
                #         },
                #         {
                #             "typeName": "dataCollector",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "LastDataCollector1, FirstDataCollector1"
                #         },
                #         {
                #             "typeName": "collectorTraining",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "CollectorTraining"
                #         },
                #         {
                #             "typeName": "frequencyOfDataCollection",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "Frequency"
                #         },
                #         {
                #             "typeName": "samplingProcedure",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "SamplingProcedure"
                #         },
                #         {
                #             "typeName": "targetSampleSize",
                #             "multiple": False,
                #             "typeClass": "compound",
                #             "value": {
                #                 "targetSampleActualSize": {
                #                     "typeName": "targetSampleActualSize",
                #                     "multiple": False,
                #                     "typeClass": "primitive",
                #                     "value": "100"
                #                 },
                #                 "targetSampleSizeFormula": {
                #                     "typeName": "targetSampleSizeFormula",
                #                     "multiple": False,
                #                     "typeClass": "primitive",
                #                     "value": "TargetSampleSizeFormula"
                #                 }
                #             }
                #         },
                #         {
                #             "typeName": "deviationsFromSampleDesign",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "MajorDeviationsForSampleDesign"
                #         },
                #         {
                #             "typeName": "collectionMode",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "CollectionMode"
                #             ]
                #         },
                #         {
                #             "typeName": "researchInstrument",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "TypeOfResearchInstrument"
                #         },
                #         {
                #             "typeName": "dataCollectionSituation",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "CharacteristicsOfDataCollectionSituation"
                #         },
                #         {
                #             "typeName": "actionsToMinimizeLoss",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "ActionsToMinimizeLosses"
                #         },
                #         {
                #             "typeName": "controlOperations",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "ControlOperations"
                #         },
                #         {
                #             "typeName": "weighting",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "Weighting"
                #         },
                #         {
                #             "typeName": "cleaningOperations",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "CleaningOperations"
                #         },
                #         {
                #             "typeName": "datasetLevelErrorNotes",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "StudyLevelErrorNotes"
                #         },
                #         {
                #             "typeName": "responseRate",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "ResponseRate"
                #         },
                #         {
                #             "typeName": "samplingErrorEstimates",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "EstimatesOfSamplingError"
                #         },
                #         {
                #             "typeName": "otherDataAppraisal",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "OtherFormsOfDataAppraisal"
                #         },
                #         {
                #             "typeName": "socialScienceNotes",
                #             "multiple": False,
                #             "typeClass": "compound",
                #             "value": {
                #                 "socialScienceNotesType": {
                #                     "typeName": "socialScienceNotesType",
                #                     "multiple": False,
                #                     "typeClass": "primitive",
                #                     "value": "NotesType"
                #                 },
                #                 "socialScienceNotesSubject": {
                #                     "typeName": "socialScienceNotesSubject",
                #                     "multiple": False,
                #                     "typeClass": "primitive",
                #                     "value": "NotesSubject"
                #                 },
                #                 "socialScienceNotesText": {
                #                     "typeName": "socialScienceNotesText",
                #                     "multiple": False,
                #                     "typeClass": "primitive",
                #                     "value": "NotesText"
                #                 }
                #             }
                #         }
                #     ]
                # },
                # "astrophysics": {
                #     "displayName": "Astronomy and Astrophysics Metadata",
                #     "fields": [
                #         {
                #             "typeName": "astroType",
                #             "multiple": True,
                #             "typeClass": "controlledVocabulary",
                #             "value": [
                #                 "Image",
                #                 "Mosaic",
                #                 "EventList",
                #                 "Cube"
                #             ]
                #         },
                #         {
                #             "typeName": "astroFacility",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "Facility1",
                #                 "Facility2"
                #             ]
                #         },
                #         {
                #             "typeName": "astroInstrument",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "Instrument1",
                #                 "Instrument2"
                #             ]
                #         },
                #         {
                #             "typeName": "astroObject",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "Object1",
                #                 "Object2"
                #             ]
                #         },
                #         {
                #             "typeName": "resolution.Spatial",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "SpatialResolution"
                #         },
                #         {
                #             "typeName": "resolution.Spectral",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "SpectralResolution"
                #         },
                #         {
                #             "typeName": "resolution.Temporal",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "TimeResolution"
                #         },
                #         {
                #             "typeName": "coverage.Spectral.Bandpass",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "Bandpass1",
                #                 "Bandpass2"
                #             ]
                #         },
                #         {
                #             "typeName": "coverage.Spectral.CentralWavelength",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "3001",
                #                 "3002"
                #             ]
                #         },
                #         {
                #             "typeName": "coverage.Spectral.Wavelength",
                #             "multiple": True,
                #             "typeClass": "compound",
                #             "value": [
                #                 {
                #                     "coverage.Spectral.MinimumWavelength": {
                #                         "typeName": "coverage.Spectral.MinimumWavelength",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "4001"
                #                     },
                #                     "coverage.Spectral.MaximumWavelength": {
                #                         "typeName": "coverage.Spectral.MaximumWavelength",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "4002"
                #                     }
                #                 },
                #                 {
                #                     "coverage.Spectral.MinimumWavelength": {
                #                         "typeName": "coverage.Spectral.MinimumWavelength",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "4003"
                #                     },
                #                     "coverage.Spectral.MaximumWavelength": {
                #                         "typeName": "coverage.Spectral.MaximumWavelength",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "4004"
                #                     }
                #                 }
                #             ]
                #         },
                #         {
                #             "typeName": "coverage.Temporal",
                #             "multiple": True,
                #             "typeClass": "compound",
                #             "value": [
                #                 {
                #                     "coverage.Temporal.StartTime": {
                #                         "typeName": "coverage.Temporal.StartTime",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "1007-01-01"
                #                     },
                #                     "coverage.Temporal.StopTime": {
                #                         "typeName": "coverage.Temporal.StopTime",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "1007-01-02"
                #                     }
                #                 },
                #                 {
                #                     "coverage.Temporal.StartTime": {
                #                         "typeName": "coverage.Temporal.StartTime",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "1007-02-01"
                #                     },
                #                     "coverage.Temporal.StopTime": {
                #                         "typeName": "coverage.Temporal.StopTime",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "1007-02-02"
                #                     }
                #                 }
                #             ]
                #         },
                #         {
                #             "typeName": "coverage.Spatial",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "SkyCoverage1",
                #                 "SkyCoverage2"
                #             ]
                #         },
                #         {
                #             "typeName": "coverage.Depth",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "200"
                #         },
                #         {
                #             "typeName": "coverage.ObjectDensity",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "300"
                #         },
                #         {
                #             "typeName": "coverage.ObjectCount",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "400"
                #         },
                #         {
                #             "typeName": "coverage.SkyFraction",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "500"
                #         },
                #         {
                #             "typeName": "coverage.Polarization",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "Polarization"
                #         },
                #         {
                #             "typeName": "redshiftType",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "RedshiftType"
                #         },
                #         {
                #             "typeName": "resolution.Redshift",
                #             "multiple": False,
                #             "typeClass": "primitive",
                #             "value": "600"
                #         },
                #         {
                #             "typeName": "coverage.RedshiftValue",
                #             "multiple": True,
                #             "typeClass": "compound",
                #             "value": [
                #                 {
                #                     "coverage.Redshift.MinimumValue": {
                #                         "typeName": "coverage.Redshift.MinimumValue",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "701"
                #                     },
                #                     "coverage.Redshift.MaximumValue": {
                #                         "typeName": "coverage.Redshift.MaximumValue",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "702"
                #                     }
                #                 },
                #                 {
                #                     "coverage.Redshift.MinimumValue": {
                #                         "typeName": "coverage.Redshift.MinimumValue",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "703"
                #                     },
                #                     "coverage.Redshift.MaximumValue": {
                #                         "typeName": "coverage.Redshift.MaximumValue",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "704"
                #                     }
                #                 }
                #             ]
                #         }
                #     ]
                # },
                # "biomedical": {
                #     "displayName": "Life Sciences Metadata",
                #     "fields": [
                #         {
                #             "typeName": "studyDesignType",
                #             "multiple": True,
                #             "typeClass": "controlledVocabulary",
                #             "value": [
                #                 "Case Control",
                #                 "Cross Sectional",
                #                 "Cohort Study",
                #                 "Not Specified"
                #             ]
                #         },
                #         {
                #             "typeName": "studyFactorType",
                #             "multiple": True,
                #             "typeClass": "controlledVocabulary",
                #             "value": [
                #                 "Age",
                #                 "Biomarkers",
                #                 "Cell Surface Markers",
                #                 "Developmental Stage"
                #             ]
                #         },
                #         {
                #             "typeName": "studyAssayOrganism",
                #             "multiple": True,
                #             "typeClass": "controlledVocabulary",
                #             "value": [
                #                 "Arabidopsis thaliana",
                #                 "Bos taurus",
                #                 "Caenorhabditis elegans",
                #                 "Danio rerio (zebrafish)"
                #             ]
                #         },
                #         {
                #             "typeName": "studyAssayOtherOrganism",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "OtherOrganism1",
                #                 "OtherOrganism2"
                #             ]
                #         },
                #         {
                #             "typeName": "studyAssayMeasurementType",
                #             "multiple": True,
                #             "typeClass": "controlledVocabulary",
                #             "value": [
                #                 "cell counting",
                #                 "cell sorting",
                #                 "clinical chemistry analysis",
                #                 "DNA methylation profiling"
                #             ]
                #         },
                #         {
                #             "typeName": "studyAssayOtherMeasurmentType",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "OtherMeasurementType1",
                #                 "OtherMeasurementType2"
                #             ]
                #         },
                #         {
                #             "typeName": "studyAssayTechnologyType",
                #             "multiple": True,
                #             "typeClass": "controlledVocabulary",
                #             "value": [
                #                 "culture based drug susceptibility testing, single concentration",
                #                 "culture based drug susceptibility testing, two concentrations",
                #                 "culture based drug susceptibility testing, three or more concentrations (minimium inhibitory concentration measurement)",
                #                 "flow cytometry"
                #             ]
                #         },
                #         {
                #             "typeName": "studyAssayPlatform",
                #             "multiple": True,
                #             "typeClass": "controlledVocabulary",
                #             "value": [
                #                 "210-MS GC Ion Trap (Varian)",
                #                 "220-MS GC Ion Trap (Varian)",
                #                 "225-MS GC Ion Trap (Varian)",
                #                 "300-MS quadrupole GC/MS (Varian)"
                #             ]
                #         },
                #         {
                #             "typeName": "studyAssayCellType",
                #             "multiple": True,
                #             "typeClass": "primitive",
                #             "value": [
                #                 "CellType1",
                #                 "CellType2"
                #             ]
                #         }
                #     ]
                # },
                # "journal": {
                #     "displayName": "Journal Metadata",
                #     "fields": [
                #         {
                #             "typeName": "journalVolumeIssue",
                #             "multiple": True,
                #             "typeClass": "compound",
                #             "value": [
                #                 {
                #                     "journalVolume": {
                #                         "typeName": "journalVolume",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "JournalVolume1"
                #                     },
                #                     "journalIssue": {
                #                         "typeName": "journalIssue",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "JournalIssue1"
                #                     },
                #                     "journalPubDate": {
                #                         "typeName": "journalPubDate",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "1008-01-01"
                #                     }
                #                 },
                #                 {
                #                     "journalVolume": {
                #                         "typeName": "journalVolume",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "JournalVolume2"
                #                     },
                #                     "journalIssue": {
                #                         "typeName": "journalIssue",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "JournalIssue2"
                #                     },
                #                     "journalPubDate": {
                #                         "typeName": "journalPubDate",
                #                         "multiple": False,
                #                         "typeClass": "primitive",
                #                         "value": "1008-02-01"
                #                     }
                #                 }
                #             ]
                #         },
                #         {
                #             "typeName": "journalArticleType",
                #             "multiple": False,
                #             "typeClass": "controlledVocabulary",
                #             "value": "abstract"
                #         }
                #     ]
                # }
            }
        }
    }
    
    return json.dumps(full_dataset_dict)