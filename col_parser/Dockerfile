FROM python

WORKDIR /root

COPY . .

RUN pip install -r requirements.txt --upgrade pip && rm requirements.txt

CMD ["bash", "download_and_parse.sh"]
