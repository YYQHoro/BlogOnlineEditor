CUR_PATH=$(dirname $(realpath "$0"))
nohup python3 $CUR_PATH/app.py >$CUR_PATH/run.log 2>&1 & echo $! > $CUR_PATH/pid
