This exports data from a CGD account.

Export transactions:

```bash
python3 cgd-export.py -v transactions 123456 678901 >transactions.json
```

Or documents:

```bash
python3 cgd-export.py -v documents 123456 678901 >documents.json
```

# Indexing and querying

Install docker:

```bash
# see https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu/#install-using-the-repository
sudo apt-get install -y apt-transport-https software-properties-common
wget -qO- https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce
docker version
```

Install docker-compose:

```bash
# see https://github.com/docker/compose/releases
# see https://docs.docker.com/compose/install
sudo curl -L https://github.com/docker/compose/releases/download/1.22.0/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

Launch Elasticsearch and Kibana:

```bash
docker-compose up -v
```

Create the Elasticsearch indices:

```bash
# NB we are using the default portuguese analyser, which means, terms will be lowercase, stop words removed, words will be stemmed (e.g. accents/diacritics do not matter and we can search by plurals or singulars).
# see https://www.elastic.co/guide/en/elasticsearch/reference/6.3/indices-create-index.html
# see https://www.elastic.co/guide/en/elasticsearch/reference/6.3/analysis-lang-analyzer.html#portuguese-analyzer
http -v put http://localhost:9200/_ingest/pipeline/document <<'EOF'
{
    "description": "Extract document from contents attachment",
    "processors": [
        {
            "attachment": {
                "field": "contents"
            }
        }
    ]
}
EOF
http -v delete http://localhost:9200/documents
http -v put http://localhost:9200/documents <<'EOF'
{
    "settings": {
        "index": {
            "number_of_shards": 5,
            "number_of_replicas": 0
        },
        "analysis": {
            "analyzer": {
                "default": { 
                    "type": "portuguese"
                }
            }
        }
    },
    "mappings": {
        "_doc": {
            "_source": {
                "enabled": true,
                "excludes": [
                    "contents"
                ]
            }
        }
    }
}
EOF
http -v delete http://localhost:9200/transactions
http -v put http://localhost:9200/transactions <<'EOF'
{
    "settings": {
        "index": {
            "number_of_shards": 5,
            "number_of_replicas": 0
        },
        "analysis": {
            "analyzer": {
                "default": { 
                    "type": "portuguese"
                }
            }
        }
    },
    "mappings": {
        "_doc": {
            "properties": {
                "details": {
                    "properties": {
                        "generalDetails": {
                            "properties": {
                                "key": {
                                    "type": "text"
                                },
                                "value": {
                                    "type": "text"
                                }
                            }
                        },
                        "balanceDetails": {
                            "properties": {
                                "key": {
                                    "type": "text"
                                },
                                "value": {
                                    "type": "text"
                                }
                            }
                        },
                        "operationSpecificDetails": {
                            "properties": {
                                "key": {
                                    "type": "text"
                                },
                                "value": {
                                    "type": "text"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
EOF
http -v http://localhost:9200/_cat/indices?v
http -v http://localhost:9200/documents/_settings
http -v http://localhost:9200/transactions/_settings
```

Test the documents analyser:

```bash
http post localhost:9200/documents/_analyze <<'EOF'
{
    "text": "Transferências e Instruções de Débito de Particulares"
}
EOF
```

Import the documents and transactions:

```bash
python3 cgd-import.py -v documents
python3 cgd-import.py -v transactions
```

See the documents and transactions mappings to known which properties are available:

```bash
http localhost:9200/documents/_mapping/_doc
http localhost:9200/transactions/_mapping/_doc
```

Do some search queries:

```bash
http -v localhost:9200/documents/_search <<'EOF'
{
    "query": {
        "query_string":{
            "query": "Transferências e Instruções de Débito de Particulares"
        }
    }
}
EOF
```

```bash
http -v localhost:9200/documents/_search <<'EOF'
{
    "query": {
        "query_string":{
            "query": "encargos"
        }
    }
}
EOF
```
