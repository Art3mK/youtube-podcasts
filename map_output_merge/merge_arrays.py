# -*- coding: utf-8 -*-

def lambda_handler(event, context):
    # [
    #     [],
    #     [
    #         "{\"videoId\": \"WDTVD-4pla0\", \"title\": \"ПАРАЗИТЫ и бактерии в МЯСЕ: как не отравиться? Кишечная палочка, ботулизм\", \"channel_title\": \"Борис Цацулин\", \"publishedDate\": \"2020-09-08T15:52:13Z\"}"
    #     ],
    # ]
    flat_list = []
    for sublist in event:
        for item in sublist:
            flat_list.append(item)
    return(flat_list)

if __name__ == "__main__":
    print(lambda_handler([["a","b"],[],["c"]],""))
