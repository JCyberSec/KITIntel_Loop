from kitintel.wrapper import search, content
import argparse
import csv
import json
import re
import time

__version__ = '5_7_24_1'

# Function to perform the 'kitintel search' command
def perform_search(searchTerm, date, number):
    """
        Perform search on KITIntel and return the JSON.

        Args:
            searchTerm (str): The input string to search.
            date (str): The time to search.
            number (int): The number of hits to return

        Returns:
            json: A json of all matching hits found on KITIntel.
    """
    try:
        result = json.loads(search(searchTerm, 'UUID', number, date))
        return result
    except Exception as e:
        raise e

# Function to perform regex against the collected content
def perform_regex(text, pattern):
        """
        Perform regex pattern matching on the given text and return all matching hits.

        Args:
            text (str): The input text to search within.
            pattern (str): The regex pattern to apply.

        Returns:
            list: A list of all matching hits (substrings) found in the text.
        """

        # Compile the regex pattern
        regex = re.compile(pattern)

        # Find all matches in the text
        matches = regex.findall(text)

        return matches

# Function to perform the 'kitintel content' command
def perform_content(uuid):
    """
        Perform content pull on KITIntel and return the text
        Args:
            json_response (str): JSON from KITIntel search

        Returns:
            string: A text string of the content.
    """
    try:
        content_text = content(uuid)
        return (content_text)
    except Exception as e:
        raise e


def generate_output(output_type, data_list, search_term):
    """
    Generate output based on the chosen output type and provided variables.

    Args:
        output_type (str): The desired output type ('text', 'json', 'csv', 'file').
        count (int): The count variable.
        uuid (str): The UUID variable.
        match (bool): The match variable.

    Returns:
        str: The generated output in the specified format.
    """
    if output_type == 'json':
        # Organize data into a dictionary by 'count'
        count_dict = {}
        for item in data_list:
            count = item['count']
            uuid = item['uuid']
            match = item['match']
            # Update count_dict with the latest data for each count
            count_dict[count] = {'uuid': uuid, 'match': match}
        
        # Convert count_dict to JSON object
        output = json.dumps(count_dict)
    
    elif output_type == 'csv':
        output = "\n".join([f"{item['count']},{item['uuid']},{item['match']}" for item in data_list])
    
    elif output_type == 'file':
        filename = f"{int(time.time())}_{search_term.replace(' ', '_')}.txt"

        with open(filename, 'w') as file:
            for item in data_list:
                file.write(f"Count: {item['count']}\nUUID: {item['uuid']}\nMatch: {item['match']}\n\n")
        output = f"Output written to {filename}"

    return output


# Main function to execute the workflow
def main(args):
    count = 0
    data_list = []
    json_response = perform_search(args.search, args.date, args.number)
    if json_response:
        # Extract UUIDs from the 'results' list in the JSON response
        uuids = [result["file"]["UUID"] for result in json_response["results"]]
        for uuid in uuids:
            content = perform_content(uuid)
            if content:
                matches = perform_regex(content, args.regex)
                if matches:
                    for match in matches:
                        count += 1
                        if args.output == 'text':
                            print (f"[{count}] - File UUID: {uuid}\t{match}")
                        else:
                            data_list.append({'count': count, 'uuid': uuid, 'match': match})

        if args.output != 'text':
            output = generate_output(args.output, data_list, args.search)
            print (output)


if __name__ == "__main__":

    items = ['csv', 'file', 'json', 'text']

    ## Argparse Arguments
    parser = argparse.ArgumentParser(prog ='KITIntel automated searching loop',
                                     description="Use this script to perform automated post processing searching on results found from KITIntel. Using an IoC, perform a search across the KITintel data set, pulling the file content for every matching file and then performing further searching on the file content to fully enrich a complex search and support a live investigation with complex data needs.",
                                    )
    parser.add_argument('-d', '--date', help='Relative date to search - Examples: 3h, 6d, 9w - Default 5y', default="5y")
    parser.add_argument('-n', '--number', help='Number of items to return - Default 100', default=100)
    parser.add_argument('-o', '--output', choices=items, help='Output type. Choose from: text, json, csv, file - Default text', default='text')
    parser.add_argument('-r', '--regex', help='Regex pattern to search across KITIntel results', required='True')
    parser.add_argument('-s', '--search', help='KITIntel Search term', required='True')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s-{version}'.format(version=__version__))

    args = parser.parse_args()
    main(args)