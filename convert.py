import json
import re

import pandas as pd
from textblob import TextBlob

regex = re.compile(r"^(top|\d+)?([\w\s]*(freelance|\d)|\w+)\s(?P<title>.+)\s(for).+$", re.IGNORECASE | re.MULTILINE)


def make_unique(list):
    res_list = []
    for i in range(len(list)):
        exist = False
        for j in list[i + 1:]:
            if list[i]['hash'] == j['hash']:
                exist = True
        if not exist:
            res_list.append(list[i])

    return res_list


if __name__ == '__main__':

    with open('upwork_categories.json', 'r') as readFile:
        items = json.loads(readFile.read())

    for i in items:
        matches = regex.search(i['title'])
        if matches:
            i['title'] = matches.groupdict()['title']

    level0 = [i for i in items if i['level'] == 0]
    level0 = make_unique(level0)

    level1 = [i for i in items if i['level'] == 1]
    level1 = make_unique(level1)

    level2 = [i for i in items if i['level'] == 2]
    level2 = make_unique(level2)

    level3 = [i for i in items if i['level'] == 3]
    level3 = make_unique(level3)

    for l2 in level2:
        l2['children'] = list([dict(title=l3['title'], link=l3['link'], children=l3['children']) for l3 in level3 if
                               l3['parent'] == l2['hash']])

    for l1 in level1:
        l1['children'] = list([dict(title=l2['title'], link=l2['link'], children=l2['children']) for l2 in level2 if
                               l2['parent'] == l1['hash']])

    for l0 in level0:
        l0['children'] = list([dict(title=l1['title'], link=l1['link'], children=l1['children']) for l1 in level1 if
                               l1['parent'] == l0['hash']])

    result = list([dict(title=l0['title'], link=l0['link'], children=l0['children']) for l0 in level0])

    dataframe = {
        "Category": [],
        "Sub Category": [],
        "Sub Sub Category": []
    }
    "".join(['a', 'b', 'c'])
    for l0 in level0:
        title0 = TextBlob(l0['title'])
        for l1 in l0['children']:
            title1 = TextBlob(l1['title'])
            for l2 in l1['children']:
                title2 = TextBlob(l2['title'])
                dataframe["Category"].append(" ".join(title0.words[:-1] + title0.words[-1:].singularize()))
                dataframe["Sub Category"].append(" ".join(title1.words[:-1] + title1.words[-1:].singularize()))
                dataframe["Sub Sub Category"].append(" ".join(title2.words[:-1] + title2.words[-1:].singularize()))
            else:
                dataframe["Category"].append(" ".join(title0.words[:-1] + title0.words[-1:].singularize()))
                dataframe["Sub Category"].append(" ".join(title1.words[:-1] + title1.words[-1:].singularize()))
                dataframe["Sub Sub Category"].append("")
        else:
            dataframe["Category"].append(" ".join(title0.words[:-1] + title0.words[-1:].singularize()))
            dataframe["Sub Category"].append("")
            dataframe["Sub Sub Category"].append("")

    df = pd.DataFrame(dataframe)
    # Create a Pandas Excel writer using XlsxWriter as the engine.
    writer = pd.ExcelWriter('categories.xlsx', engine='xlsxwriter')

    # Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(writer, sheet_name='Categories')

    # Close the Pandas Excel writer and output the Excel file.
    writer.close()
    with open('converted_categories.json', 'w') as f:
        f.write(json.dumps(result, indent=2))
