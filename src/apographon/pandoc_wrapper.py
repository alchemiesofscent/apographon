import subprocess
import os

class PandocWrapper:
    def __init__(self, input_file, output_file, format):
        self.input_file = input_file
        self.output_file = output_file
        self.format = format

    def convert(self):
        command = ['pandoc', self.input_file, '-o', self.output_file, '--from', 'html', '--to', self.format]
        try:
            subprocess.run(command, check=True)
            print(f"Successfully converted {self.input_file} to {self.output_file} in {self.format} format.")
        except subprocess.CalledProcessError as e:
            print(f"Error during conversion: {e}")
            raise

    def convert_to_tei(self):
        self.format = 'tei'
        self.output_file = os.path.splitext(self.input_file)[0] + '.xml'
        self.convert()
