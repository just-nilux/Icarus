# Purpose
**generate_report** module  exists because of the inabilities of visualize_analyzer module, on demonstrating the statistics like "how many times an uptrend occured", "what are the features of these trends", "when you compare the trends on BTCUSDT and ETHUSDT what are the similarities"...
# Vision
**generate_report** module, 
1. receives input from analyzer module
2. feeds the analyzed data to functions that creates statistics out of them
3. and finally dumps the statistics in various formats
# Functionalities
* Receiving inputs from
    * analyzer module
    * statistics on database
* Dumping results (images, tables)
    * to database
    * markdown files
    * to folders
* Organize markdown files

# Configuration
## Config fields:
* **source:** 

## Read analysis data from analysis dict
Indices of reporters: reporter x timeframes x pairs x analyzers

    "report": {
        "market_class_table_stats": {
            "source": "analyzer",
            "analyzers": [
                "market_class_aroon",
                "market_class_aroonosc",
                "market_class_fractal_aroon"
            ],
            "writers": [
                "markdown_table",
                "database"
            ]
        }
    }

## Read analysis data from database
Indices of reporters: reporter x timeframes x pairs x analyzers


    "report": {
        "market_class_table_stats": {
            "source": "database",
            "analyzers": [
                "market_class_aroon",
                "market_class_aroonosc",
                "market_class_fractal_aroon"
            ],
            "writers": [
                "markdown_table",
                "database"
            ]
        }
    }

## Read multiple and/or custom fields from analysis dict
The "analyzers" field enables indices to be created in the following format: _reporter x timeframes x pairs x analyzers_. Instead "indices" field enables multiple field from analysis_dict to be fed in to reporter


    "report": {
        "market_class_table_stats": {
            "source": "analyzer"
            "indices": [
                ["BTCUSDT","1d", "close"],
                ["ETHUSDT","1d", "close"],
                ["XRPUSDT","1d", "close"]
            ],
            "writers": [
                "markdown_table",
                "database"
            ]
        }
    }