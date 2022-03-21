FROM python:3.9

# Install tarquin
RUN apt-get update -y && apt-get install -y gnuplot ghostscript
RUN mkdir ../tarquin_folder
RUN wget -O tarquin.tar.gz https://sourceforge.net/projects/tarquin/files/TARQUIN_4.3.11/TARQUIN_Linux_4.3.11.tar.gz/download
RUN tar -xzf tarquin.tar.gz -C ../tarquin_folder
RUN rm tarquin.tar.gz
RUN mv ../tarquin_folder/TARQUIN_Linux_4.3.11_RC/tarquin /usr/local/bin/tarquin
RUN ln -s /usr/bin/gnuplot /usr/local/bin/gnuplot

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
#RUN pip install --no-dependencies pydicom==1.4.2
RUN git clone --recurse-submodules https://git.fmrib.ox.ac.uk/fsl/fsl_mrs.git
RUN cd fsl_mrs && pip install .
RUN cd ..

RUN sed -i '/disable ghostscript format types/,+6d' /etc/ImageMagick-6/policy.xml

COPY mrs/ mrs/
COPY config/ config/

CMD ["python", "main.py"]