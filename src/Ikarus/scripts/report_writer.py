

def write_to_image(indices, report_dict):
    print('Writing to image')
    print('Indice:', str(indices))
    print('Data:', str(report_dict))
    pass

def write_to_markdown(indices, report_dict):
    pass

def write_to_database(indices, report_dict):
    pass

class ReportWriter():
    def write(self, indice, report_dict):
        pass
    pass

class ImageWriter(ReportWriter):
    def __init__(self, target_folder) -> None:
        super().__init__()
        self.target_folder = target_folder
        # Create if the target folder does not exist

    def write(self, indice, report_dict):
        reporter, timeframe, symbol, analyzer = indice

        target_path = '{}_{}_{}_{}_{}'.format(
            self.target_folder,reporter,timeframe,symbol,analyzer)
        print('Writing to image to:', target_path)
        print('Indice:', str(indice))
        print('Data:', str(report_dict))
        pass

class MarkdownWriter(ReportWriter):
    pass

class DatabaseWriter(ReportWriter):
    pass