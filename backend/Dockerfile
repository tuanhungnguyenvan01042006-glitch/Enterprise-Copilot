
#Vai trò của file này : 
#build một “container” cho ứng dụng backend Python.
# ta thấy phần code bên dưới đang tải về Thư viện, môi trường cần thiết,
#x như copy các file, thư mục của backend (src code) để đóng gói vào Container 
# Vai trò sâu xa : 
#    + Tạo ra môi trường chạy backend chạy nhất quán trên mọi máy
#    + Ko cần cài Python và Dependency thủ công trên từng server
#    + Dùng cùng Docker Compose để khởi động service backend 

# Nó liên quan mật thiết đến hàm build.context trong compose.yaml, nhưng thật sự mình chưa hiểu cách hoạt động lắm
# Nch nó đóng vai trò, hướng dẫn cho Image / Container biết đóng gói cái gì với Backend (và cả frontend cũng tương tự)


FROM python:3.12-slim   
#lấy base image Python :  chọn version 3.12, bản slim --> Giúp Docker bt phải chạy Backend với Python j  

# thiết lập biến môi trường cho Container (chứ ko phải môi trường của src code): nch là cx đ hiểu vai trò lắm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app      

COPY requirements.txt ./requirements.txt

#Copy file requirements.txt từ máy chủ (host) vào thư mục /app/requirements.txt trong container.
#Docker lấy file dependency list (danh sách thư viện chạy trong src code backend) từ máy của bạn và đưa vào container


RUN pip install --no-cache-dir -r requirements.txt  # install thư viện trong file requirement

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN mkdir -p /app/storage/uploads

