# !/usr/bin/env python
# -*- coding:utf-8 -*-


import os
import global_constant
import re
import yaml
import datetime

DateUtil = global_constant.dateUtil


class YamlParser(object):
    def vars_map(self, key, value, init_day, format='%Y-%m-%d'):
        init_date = DateUtil.parse_date(init_day, format)
        if key == 'today':
            if value is None:
                return DateUtil.get_now_fmt('%Y-%m-%d', init_date)
            else:
                return value
        elif key == 'yesterday':
            if value is None:
                return DateUtil.get_yesterday_fmt('%Y-%m-%d', init_date)
            else:
                return value
        elif key == 'intervalday':
            if value is None:
                raise Exception("interval day is none")
            return DateUtil.get_interval_day_fmt(int(value), '%Y-%m-%d', init_date)
        elif key == 'lastMonth':
            if value is None:
                return DateUtil.get_last_month(init_date)
            else:
                return value
        elif key == 'currentMonth':
            if value is None:
                return DateUtil.get_current_month(init_date)
            else:
                return value
        elif key == 'yesterdayMonth':
            if value is None:
                return DateUtil.get_yesterday_month(init_date)
            else:
                return value

        elif key == 'pre_1_hours_day':
            # 前1小时所在日期
            if value is None:
                return DateUtil.get_add_hours_day(init_date, -1)
            else:
                return value
        elif key == 'pre_1_hours_hour':
            # 前1小时所在小时
            if value is None:
                return DateUtil.get_add_hours_hour(init_date, -1)
            else:
                return value
        elif key == 'pre_2_hours_day':
            # 前1小时所在日期
            if value is None:
                return DateUtil.get_add_hours_day(init_date, -2)
            else:
                return value
        elif key == 'pre_2_hours_hour':
            # 前1小时所在小时
            if value is None:
                return DateUtil.get_add_hours_hour(init_date, -2)
            else:
                return value
        else:
            return value

    '''
    返回 包含sql,vars
    '''

    def parse_hive_sql(self, step_dict, init_day, fmt='%Y-%m-%d'):
        vars = []
        sqls = []
        sql_paths = []
        if step_dict.has_key('vars'):
            vars_dict = step_dict['vars']
            if vars_dict is not None and len(vars_dict) > 0:
                for (var_key, var_value_dict) in vars_dict.items():
                    var_type = var_value_dict['type']
                    if var_value_dict.has_key('value'):
                        var_value = var_value_dict['value']
                    map_value = self.vars_map(var_key, var_value, init_day, format=fmt)
                    if var_type == "string":
                        vars.append("set hivevar:" + str(var_key) + "='" + str(map_value) + "';")
                    else:
                        vars.append("set hivevar:" + str(var_key) + "=" + str(map_value) + ";")
        if step_dict.has_key('sqls'):
            sql_list = step_dict['sqls']
            if sql_list and len(sql_list) > 0:
                for sql_dict in sql_list:
                    sql_dict_value = sql_dict['sql']
                    if sql_dict_value.has_key('value') and sql_dict_value['value']:
                        sqls.append(sql_dict_value['value'])
                    if sql_dict_value.has_key('path') and sql_dict_value['path']:
                        sql_paths.append(sql_dict_value['path'])
        return (vars, sqls, sql_paths)



    def parse_export(self, python_path, project_path, step_dict, init_day, fmt):
        command_list = []
        if step_dict.has_key('ops'):
            ops_list = step_dict['ops']
            if ops_list and len(ops_list) > 0:
                for ops_dict in ops_list:
                    for (command_key, command_value) in ops_dict.items():
                        command_list.append(self.export_command(python_path,
                                                                project_path,
                                                                command_key,
                                                                command_value, init_day,fmt))
        return command_list

    '''
    替换变量
    '''

    def replace_sql_param(self, sql, vars_dict, init_day, format=None):
        p = re.compile(r"\$\{[^\}\$ ]+\}")
        m = p.findall(sql)
        if m and len(m) > 0:
            for key in m:
                var = key.replace("${", "")
                var = var.replace("}", "")
                default_value = None
                print(vars_dict)
                if vars_dict and vars_dict[var] and vars_dict[var].has_key('value') and vars_dict[var]['value']:
                    default_value = str(vars_dict[var]['value'])
                sql = sql.replace(key, self.vars_map(var, default_value, init_day, format))
        return sql

    def replace_mysql_db(self, mysql_db, init_day):
        """
        处理 mysql 按天分表
        """
        if mysql_db.startswith("beeper2_location.point_"):
            process_day = datetime.datetime.strptime(init_day, '%Y-%m-%d') + datetime.timedelta(days=-1)
            process_day = datetime.datetime.strftime(process_day, '%Y_%m_%d')
            mysql_db = mysql_db.replace("${yesterday}", process_day)
        return mysql_db

    def export_command(self, python_path, project_path, command_key, command_value, init_day, fmt):
        mysql2hive = project_path + '/export/mysql2hive.py'
        mongo2hive = project_path + '/export/mongo2hive.py'
        hive2mysql = project_path + '/export/hive2mysql.py'
        hive2clickhouse = project_path + '/export/hive2clickhouse.py'
        hive2kafka = project_path + '/export/hive2kafka.py'
        kafka2hdfs = project_path + '/export/kafka2hdfs.py'
        hive2excel = project_path + '/export/hive2excel.py'
        odps2hive = project_path + '/export/odps2hive.py'
        hiveserver2hive = project_path + '/export/hiveserver2hive.py'
        command_list = []
        command_list.append(python_path)
        if command_key == 'mysql2hive':
            command_list.append(mysql2hive)
            command_list.append("--from")
            # mysql 分表处理
            mysql_db = self.replace_mysql_db(command_value['mysql_db'], init_day)
            command_list.append(mysql_db)
            command_list.append("--to")
            command_list.append(command_value['hive_db'])
            if command_value.has_key("mysql_instance"):
                command_list.append("--instance")
                command_list.append(command_value["mysql_instance"])
            else:
                command_list.append("--instance")
                command_list.append("business")
            if command_value.has_key("include_columns") and command_value['include_columns']:
                command_list.append("--columns")
                command_list.append(command_value['include_columns'])
            if command_value.has_key("exclude_columns") and command_value['exclude_columns']:
                command_list.append("--exclude-columns")
                command_list.append(command_value['exclude_columns'])
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key("partition") and command_value['partition']:
                command_list.append("--partition")
                partition_value = command_value['partition']
                partition_value = self.replace_sql_param(partition_value, vars, init_day, fmt)
                command_list.append(partition_value)
            if command_value.has_key("where") and command_value['where']:
                command_list.append("--where")
                partition_value = command_value['where']
                partition_value = self.replace_sql_param(partition_value, vars, init_day, fmt)
                command_list.append(partition_value)
            if command_value.has_key("query_sql") and command_value['query_sql']:
                command_list.append("--query-sql")
                command_list.append(command_value['query_sql'])
            return command_list
        if command_key == 'mongo2hive':
            command_list.append(mongo2hive)
            command_list.append("--file")
            command_list.append(command_value["yaml_file"])
            command_list.append("--from")
            command_list.append(command_value["mongo_db"])
            command_list.append("--to")
            command_list.append(command_value["hive_db"])
            command_list.append("--init")
            if init_day is None:
                init_day = DateUtil.get_now_fmt()
            command_list.append(init_day)
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key('partition') and command_value['partition']:
                command_list.append("--partition")
                partition_value = command_value['partition'].strip()
                partition_value = self.replace_sql_param(partition_value, vars, init_day, fmt)
                command_list.append(partition_value)
            return command_list
        if command_key == 'hive2mysql':
            command_list.append(hive2mysql)
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key("delete_sql") and command_value["delete_sql"]:
                command_list.append("--sql")
                sql = self.replace_sql_param(command_value["delete_sql"], vars, init_day, fmt)
                command_list.append(sql)
            if command_value.has_key("query") and command_value["query"]:
                command_list.append("--query")
                hql = self.replace_sql_param(command_value["query"], vars, init_day, fmt)
                command_list.append(hql)
            if command_value.has_key("mysql_instance"):
                command_list.append("--instance")
                command_list.append(command_value["mysql_instance"])
            else:
                command_list.append("--instance")
                command_list.append("bi_result")
            command_list.append("--hive")
            command_list.append(command_value['hive_db'])
            command_list.append("--to")
            command_list.append(command_value['mysql_db'])
            command_list.append("--columns")
            command_list.append(command_value['mysql_columns'])
            return command_list
        if command_key == 'hive2clickhouse':
            command_list.append(hive2clickhouse)
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key("delete_sql") and command_value["delete_sql"]:
                command_list.append("--delete_sql")
                sql = self.replace_sql_param(command_value["delete_sql"], vars, init_day, fmt)
                command_list.append(sql)
            if command_value.has_key("query") and command_value["query"]:
                command_list.append("--query")
                hql = self.replace_sql_param(command_value["query"], vars, init_day, fmt)
                command_list.append(hql)
            if command_value.has_key("clickhouse_cluster"):
                command_list.append("--clickhouse_cluster")
                command_list.append(command_value["clickhouse_cluster"])
            else:
                command_list.append("--clickhouse_cluster")
                command_list.append("secoo_cluster_one")
            command_list.append("--hive")
            command_list.append(command_value['hive_db'])
            command_list.append("--to")
            command_list.append(command_value['clickhouse_db_table'])
            command_list.append("--columns")
            command_list.append(command_value['clickhouse_columns'])
            command_list.append("--type")
            command_list.append("export")
            command_list.append("--op")
            command_list.append("hive2clickhouse")
            command_list.append("--spark_submit_conf")
            command_list.append(command_value['spark_submit_conf'])
            return command_list
        if command_key == 'hive2kafka':
            command_list.append(hive2kafka)
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key("query") and command_value["query"]:
                command_list.append("--query")
                hql = self.replace_sql_param(command_value["query"], vars, init_day, fmt)
                command_list.append(hql)
            if command_value.has_key("kafka_cluster"):
                command_list.append("--kafka_cluster")
                command_list.append(command_value["kafka_cluster"])

            command_list.append("--hive")
            command_list.append(command_value['hive_db'])
            command_list.append("--to")
            command_list.append(command_value['kafka_topic'])
            if command_value.has_key("kafka_producer_conf"):
                command_list.append("--kafka_producer_conf")
                command_list.append(command_value["kafka_producer_conf"])
            command_list.append("--type")
            command_list.append("export")
            command_list.append("--op")
            command_list.append("hive2kafka")
            command_list.append("--spark_submit_conf")
            command_list.append(command_value['spark_submit_conf'])
            return command_list
        if command_key == 'kafka2hdfs':
            command_list.append(kafka2hdfs)
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key("kafka_cluster"):
                command_list.append("--kafka_cluster")
                command_list.append(command_value["kafka_cluster"])
            command_list.append("--kafka_topic")
            command_list.append(command_value['kafka_topic'])
            if command_value.has_key("consumer_group"):
                command_list.append("--consumer_group")
                command_list.append(command_value["consumer_group"])
            command_list.append("--hdfs_path")
            hdfs_path = self.replace_sql_param(command_value["hdfs_path"], vars, init_day, fmt)
            command_list.append(hdfs_path)
            if command_value.has_key("kafka_consumer_conf"):
                command_list.append("--kafka_consumer_conf")
                command_list.append(command_value["kafka_consumer_conf"])
            command_list.append("--type")
            command_list.append("export")
            command_list.append("--op")
            command_list.append("kafka2hdfs")
            return command_list
        if command_key == 'hive2excel':
            command_list.append(hive2excel)
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            command_list.append("--name")
            command_list.append(command_value['excel_name'])
            command_list.append("--subject")
            command_list.append(command_value['email_subject'])
            command_list.append("--content")
            command_list.append(command_value['email_content'])
            if command_value.has_key("hive_db"):
                command_list.append("--tables")
                command_list.append(command_value['hive_db'])
            if command_value.has_key("query_sql"):
                command_list.append("--query_sql")
                query_sql = self.replace_sql_param(command_value["query_sql"], vars, init_day, fmt)
                command_list.append(query_sql)
            # 邮件输出类型(附件 or 邮件正文html)
            command_list.append("--output")
            if 'output_type' in command_value:
                command_list.append(command_value['output_type'])
            # 如果没有配置output_type, 默认走附件类型
            else:
                command_list.append('attachment')
            command_list.append("--receivers")
            command_list.append(command_value['email_receivers'])
            return command_list
        if command_key == 'odps2hive':
            command_list.append(odps2hive)
            command_list.append("--from")
            command_list.append(command_value['odps_db'])
            command_list.append("--to")
            command_list.append(command_value['hive_db'])
            if command_value.has_key("include_columns") and command_value['include_columns']:
                command_list.append("--columns")
                command_list.append(command_value['include_columns'])
            if command_value.has_key("exclude_columns") and command_value['exclude_columns']:
                command_list.append("--exclude-columns")
                command_list.append(command_value['exclude_columns'])
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key('partition') and command_value['partition']:
                command_list.append("--partition")
                partition_value = command_value['partition'].strip()
                partition_format = None
                if command_value.has_key('partition_format') and command_value['partition_format']:
                    partition_format = command_value['partition_format'].strip()
                partition_value = self.replace_sql_param(partition_value, vars, init_day, partition_format, fmt)
                command_list.append(partition_value)
            return command_list
        if command_key == 'hiveserver2hive':
            command_list.append(hiveserver2hive)
            command_list.append("--server")
            command_list.append(command_value["hiveserver2_server"])
            command_list.append("--from")
            command_list.append(command_value['hiveserver2_db'])
            command_list.append("--to")
            command_list.append(command_value['hive_db'])
            if command_value.has_key("include_columns") and command_value['include_columns']:
                command_list.append("--columns")
                command_list.append(command_value['include_columns'])
            vars = {}
            if command_value.has_key("vars") and command_value["vars"]:
                vars = command_value["vars"]
            if command_value.has_key("partition") and command_value['partition']:
                command_list.append("--partition")
                partition_value = command_value['partition']
                partition_value = self.replace_sql_param(partition_value, vars, init_day, fmt)
                command_list.append(partition_value)
            if command_value.has_key("where") and command_value['where']:
                command_list.append("--where")
                partition_value = command_value['where']
                partition_value = self.replace_sql_param(partition_value, vars, init_day, fmt)
                command_list.append(partition_value)
            if command_value.has_key("query_sql") and command_value['query_sql']:
                command_list.append("--query-sql")
                command_list.append(command_value['query_sql'])
            return command_list

# for test
if __name__ == '__main__':
    # 需要跑全部的 yaml 文件解析测试
    basedir = "/Users/yxl/yunniao/source/beeper_data_warehouse/job/script"
    yaml_files = []
    # for subdir in os.listdir(basedir):
    #     for file in os.listdir(basedir + "/" + subdir):
    #         yaml_files.append(basedir + "/" + subdir + "/" + file)
    yaml_files = [basedir + '/ods/ods_to_driver_exceptions.yml']
    init_day = '2016-01-03'
    for yaml_file in yaml_files:
        yaml_file_handler = open(yaml_file, 'r')
        yaml_sql_path = "/job/sql"
        yaml_parser = YamlParser()
        yaml_dict = yaml.safe_load(yaml_file_handler)
        print yaml_dict
        steps = yaml_dict['steps']
        if steps and len(steps) > 0:
            for step in steps:
                step_type = step['type']
                if step_type == 'hive':
                    (vars, sqls, sql_paths) = yaml_parser.parse_hive(step, init_day)
                    print "vars:", len(vars), vars
                    print "sqls:", len(sqls), sqls
                    print "sql_paths", len(sql_paths), sql_paths
                if step_type == 'export':
                    command_list = yaml_parser.parse_export("", "", step, init_day)
                    if command_list and len(command_list) > 0:
                        for command in command_list:
                            print command