FROM python:3.9-slim

# Install tarquin
RUN apt-get update -y && apt-get install -y gnuplot ghostscript git wget imagemagick
RUN mkdir ../tarquin_folder
RUN wget -O tarquin.tar.gz https://sourceforge.net/projects/tarquin/files/TARQUIN_4.3.11/TARQUIN_Linux_4.3.11.tar.gz/download
RUN tar -xzf tarquin.tar.gz -C ../tarquin_folder
RUN rm tarquin.tar.gz
RUN mv ../tarquin_folder/TARQUIN_Linux_4.3.11_RC/tarquin /usr/local/bin/tarquin
RUN ln -s /usr/bin/gnuplot /usr/local/bin/gnuplot

COPY requirements.txt mrs/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r mrs/requirements.txt

RUN sed -i '/disable ghostscript format types/,+6d' /etc/ImageMagick-6/policy.xml
COPY mrs/ mrs/mrs/
COPY config/ mrs/config/
COPY main.py mrs/main.py

WORKDIR /mrs

ENV MANIFEST_PATH=mrs/config/manifest.json

CMD ["python", "main.py"]