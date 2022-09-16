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

    "report": {
        "market_class_statistics": ["market_class_aroon", "market_class_aroonosc", "market_class_fractal_aroon" ]
    },