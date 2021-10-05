# FROM public.ecr.aws/lambda/python:3.8

# RUN yum install -y libsndfile-devel

# COPY requirements.txt  .
# RUN  pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# RUN pip3 install pip install soundfile --target "${LAMBDA_TASK_ROOT}"


FROM code.chs.usgs.gov:5001/fort/docker-containers/nabat-ml

# Copy function code
COPY endpoint.py ${LAMBDA_TASK_ROOT}
COPY spectrogram ${LAMBDA_TASK_ROOT}
COPY prediction/tf-models/ ${LAMBDA_TASK_ROOT}
COPY example.wav ${LAMBDA_TASK_ROOT}


RUN mkdir -m 777 /tmp/NUMBA_CACHE_DIR /tmp/MPLCONFIGDIR
ENV NUMBA_CACHE_DIR=/tmp/NUMBA_CACHE_DIR/
ENV MPLCONFIGDIR=/tmp/MPLCONFIGDIR/

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "endpoint.handler" ] 