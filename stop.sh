CUR_PATH=$(dirname $(realpath "$0"))
kill `cat $CUR_PATH/pid`
rm $CUR_PATH/pid
