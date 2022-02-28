FROM python:3.9

# Install tarquin
RUN mkdir ../tarquin_folder && wget -O tarquin.tar.gz https://sourceforge.net/projects/tarquin/files/TARQUIN_4.3.11/TARQUIN_Linux_4.3.11.tar.gz/download && tar -xzf tarquin.tar.gz -C ../tarquin_folder && rm tarquin.tar.gz && mv ../tarquin_folder/TARQUIN_Linux_4.3.11_RC/tarquin /usr/local/bin/tarquin && ln -s /usr/bin/gnuplot /usr/local/bin/gnuplot

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY mrs/ mrs/
COPY application.py application.py
COPY config/manifest.json manifest.json

CMD ["python", "main.py"]