import os
import numpy as np
import argparse

def extract_data(line):
    """
    Checks for the proper format as described by the FEC Dictionary (21 values), extracts neccessary data from the full
    line of pipe separated values in the line from the input file, and appends three more items as place holders for the
    running median, donation count, and total donation amount.
    :param line: line of pipe separated values
    :return: record_data: list of [cmte_id, zip_code, transaction date, transaction amount, other_id]
    """
    record = line.strip('\n').split('|')
    # Check to see if the line of data is in the format described by the FEC data dictionary. Each line needs to have
    # 21 pipe-separated values
    if len(record) != 21:
        record_data = False
    else:
        # Extract cmte_id, zipcode, date, transaction amount, and other id from full line of data
        record_data = [record[i] for i in [0, 10, 13, 14, 15]]
        record_data.extend((record_data[3], 1, record_data[3]))
        # Strip any spaces from the zipcode data and extract the first five numbers
        record_data[1] = record_data[1].strip(" ")[0:5]
    return record_data

def check_zip_data_requirements(line_of_data):
    """
    Check data for relevancy using the rules defined in the data considerations section
            Check that CMTE_ID exists
            Check that ZIP_CODE is the correct length and not empty
            Check to make sure that the TRANSACTION_AMT is not empty
            Check to make sure that OTHER_ID is empty
            If any of these are true the row is skipped
    :param line_of_data: relevant data extracted from line of input data file
    :return: good_data = True if requirements are met, False if not
    """
    good_data = True
    if line_of_data[0] == '' or len(line_of_data[1].strip(" ")) != 5 or line_of_data[1].strip(" ") == '' \
            or line_of_data[3] == '' or line_of_data[4] != '':
        good_data = False
    return good_data


def update_donations(data,donations_dictionary):
    """
    Adds each line of data's
    :param data: numpy recarry of one row of the data of interest.
    :param donations_dictionary: dictionary with the structure {cmte_id:{zip_code:[donations]}}
    :return: data: numpy recarray of data with new calculated columns included
             donations_dictionary: dictionary with cmte_id's zip code updated with new donations from the input data
    """
    cmte_id = data.CMTE_ID.item()
    zip_code = data.ZIP_CODE.item()
    trans_amt = data.TRANS_AMT.item()

    # Fill in dictionary with each unique candidate/zip code and that zip code's transaction amounts
    if cmte_id in donations_dictionary.keys():

        if zip_code in donations_dictionary[cmte_id].keys():
            donations_dictionary[cmte_id][zip_code].append(trans_amt)
        else:
            donations_dictionary[cmte_id][zip_code] = [trans_amt]
    else:
        donations_dictionary[cmte_id] = {zip_code: [trans_amt]}

    # Calculate fields of interest and store them in the proper columns of the recarray
    data.MEDIAN_AMT_BY_ZIP = round(np.median(donations_dictionary[cmte_id][zip_code]).item(), 0)
    data.TOTAL_AMT = np.sum(donations_dictionary[cmte_id][zip_code])
    data.DONATION_COUNT = len(donations_dictionary[cmte_id][zip_code])

    return data, donations_dictionary

def medianvals_by_zip(input_filepath, output_filepath_zipcodes=os.getcwd()+'/medainval_by_zip.txt'):
    """
    Opens input file of individual political contributions as a stream, reads each line of data, calculates the running median, total
    number of donations, and total donation amounts for each candidate by zipcode. Writes out a pipe separated txt file
    with each newline including the candidate ID number, zipcode, and running statistics for the corresponding input row.

    :param input_filepath: path to data file for input
    :param output_filepath: path for .txt file output
    :return: output_records
    """
    with open(input_filepath,'r') as f:
        # Define variable types of each possible column
        records_dt = np.dtype([('CMTE_ID','|S10'),('ZIP_CODE', '|S10'),('TRANS_DT','|S10'),('TRANS_AMT',np.float64),
                               ('OTHER_ID', '|S10'),('MEDIAN_AMT_BY_ZIP',np.int64),('DONATION_COUNT',np.int64),('TOTAL_AMT',np.int64)])

        #Create recarray shell for the records that will be part of the output file
        records = np.recarray((1,),dtype=records_dt)

        # Read data file line by line and add relevant data to a dictionary.
        # Dictionary Structure = { CMTE_ID : {ZIP_CODE : [TRANS_AMT,TRANS_AMT], ZIP_CODE : [TRANS_AMT,TRANS_AMT]},
        # CMTE_ID : {TRANS_DT : [TRANS_AMT(s)]}, etc. }
        candidates = {}
        for line in f:

            # Extract relevant data from the line of data
            relevant_data = extract_data(line)
            if relevant_data == False:
                continue
            # Check data for formatting and other requirements
            data_check = check_zip_data_requirements(relevant_data)
            if data_check == False:
                continue

            # Create numpy recarray of relevant data for value easier accession
            relevant_data = np.rec.array(relevant_data,dtype=records_dt)

            # Fill in dictionary with each unique candidate/zip code and that zip code's transaction amounts and update
            # relevant_data with appropriate calculated medians, counts, and sums.
            relevant_data, candidates = update_donations(relevant_data,candidates)

            # Add this data to the records array
            records = np.vstack((records, relevant_data))

            # Create numpy array of all relevant records and strip the first row which was present as a placeholder
            output_records = np.hstack((records['CMTE_ID'], records['ZIP_CODE'], records['MEDIAN_AMT_BY_ZIP'],
                                        records['DONATION_COUNT'], records['TOTAL_AMT']))
            output_records = np.delete(output_records, (0), axis=0)

        # Output output_records array to the correct folder as medianvals_by_date.txt
        np.savetxt(output_filepath_zipcodes,output_records, delimiter='|', fmt="%s")

    f.close()
    return output_records

if __name__ == '__main__':
    # Checks that the input file and output file sources are both present when running from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file',
                        help='filepath containing input data')
    parser.add_argument('output_file',
                        help='filepath to store output data')
    args = parser.parse_args()
    input_filepath = args.input_file
    output_filepath_zipcodes = args.output_file
    medianvals_by_zip(input_filepath,output_filepath_zipcodes)