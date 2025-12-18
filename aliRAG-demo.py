import os
from alibabacloud_bailian20231229 import models as bailian_20231229_models
from alibabacloud_bailian20231229.client import Client as bailian20231229Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

# 设置环境变量（您提供的信息），建议写到.env文件中调用或更新到环境变量
os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'] = '****' # 您的阿里云访问密钥ID
os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'] = '*****'# 您的阿里云访问密钥密码
os.environ['WORKSPACE_ID'] = '******'# 您的阿里云百炼业务空间ID，注意设置给用户所有权限！

# 知识库ID
INDEX_ID = '******'# 该业务空间中的知识库ID，注意设置给用户所有权限！

def create_client() -> bailian20231229Client:
    """
    创建并配置客户端（Client）。

    返回:
        bailian20231229Client: 配置好的客户端（Client）。
    """
    config = open_api_models.Config(
        access_key_id=os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_ID'),
        access_key_secret=os.environ.get('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
    )
    # 下方接入地址以公有云的公网接入地址为例，可按需更换接入地址。
    config.endpoint = 'bailian.cn-beijing.aliyuncs.com'
    return bailian20231229Client(config)

def retrieve_index(client, workspace_id, index_id, query):
    """
    在指定的知识库中检索信息。
        
    参数:
        client (bailian20231229Client): 客户端（Client）。
        workspace_id (str): 业务空间ID。
        index_id (str): 知识库ID。
        query (str): 原始输入prompt。

    返回:
        阿里云百炼服务的响应。
    """
    headers = {}
    retrieve_request = bailian_20231229_models.RetrieveRequest(
        index_id=index_id,
        query=query
    )
    runtime = util_models.RuntimeOptions()
    return client.retrieve_with_options(workspace_id, retrieve_request, headers, runtime)

def retrieve_from_knowledge_base(query):
    """
    从知识库中检索相关信息
    
    参数:
    query: 检索问题
    """
    try:
        # 创建客户端
        client = create_client()
        workspace_id = os.environ.get('WORKSPACE_ID')
        
        # 调用检索函数
        response = retrieve_index(client, workspace_id, INDEX_ID, query)
        
        # 解析并格式化输出响应
        if response.body and response.body.data:
            # 检查不同的可能属性名
            documents = None
            if hasattr(response.body.data, 'documents'):
                documents = response.body.data.documents
            elif hasattr(response.body.data, 'results'):
                documents = response.body.data.results
            elif hasattr(response.body.data, 'nodes'):
                documents = response.body.data.nodes
            
            if documents:
                # 只显示前5个记录
                display_count = min(5, len(documents))
                print(f"\n检索成功！找到 {len(documents)} 个相关文档，显示前 {display_count} 个\n")
                
                for i, doc in enumerate(documents[:5], 1):  # 只取前5个文档
                    print(f"--- 文档 {i} ---")
                    
                    # 提取相关度得分
                    score = getattr(doc, 'score', getattr(doc, 'Score', None))
                    if score is not None:
                        print(f"相关度得分: {score}")
                    
                    # 提取文档内容
                    content = ""
                    text_attr_names = ['text', 'document_text', 'content', 'Text']
                    for attr_name in text_attr_names:
                        if hasattr(doc, attr_name):
                            content = getattr(doc, attr_name)
                            break
                    
                    # 如果从Text属性获取内容，可能是嵌套的
                    if not content and hasattr(doc, 'Text'):
                        content = doc.Text
                    
                    # 提取元数据
                    metadata = getattr(doc, 'metadata', getattr(doc, 'Metadata', None))
                    if metadata:
                        # 如果metadata是一个对象，尝试提取其内容属性
                        if hasattr(metadata, 'content'):
                            content = metadata.content
                    
                    # 如果是nodes类型的数据，尝试从to_map()获取内容
                    if not content and hasattr(doc, 'to_map'):
                        try:
                            map_data = doc.to_map()
                            # 尝试从map_data中提取内容
                            if 'Text' in map_data:
                                content = map_data['Text']
                            elif 'content' in map_data:
                                content = map_data['content']
                            elif 'document_text' in map_data:
                                content = map_data['document_text']
                        except:
                            pass
                    
                    # 解析内容中的关键字段
                    if content:
                        # 如果内容是字典格式的字符串，尝试解析
                        if isinstance(content, str) and (content.startswith('#') or '记录编号:' in content or '隐患类型:' in content):
                            # 清理内容中的多余换行和特殊字符
                            content = content.replace('\n\n', '\n').strip()
                            
                            # 提取关键信息字段
                            lines = content.split('\n')
                            record_info = {}
                            current_field = ""
                            
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                    
                                if line.startswith('记录编号:') or line.startswith('数据编号:') or \
                                   line.startswith('检查对象:') or line.startswith('隐患类型:') or \
                                   line.startswith('隐患描述:') or line.startswith('检查依据:') or \
                                   line.startswith('适用地区:') or line.startswith('整改建议:') or \
                                   line.startswith('法律责任:'):
                                    parts = line.split(':', 1)
                                    if len(parts) == 2:
                                        field_name = parts[0].strip()
                                        field_value = parts[1].strip()
                                        record_info[field_name] = field_value
                                        current_field = field_name
                                    else:
                                        current_field = line.rstrip(':')
                                        record_info[current_field] = ""
                                elif current_field:
                                    # 继续添加到当前字段（处理换行内容）
                                    if record_info[current_field]:
                                        record_info[current_field] += " " + line
                                    else:
                                        record_info[current_field] = line
                            
                            # 格式化输出关键信息
                            for field, value in record_info.items():
                                print(f"{field}: {value}")
                        else:
                            # 直接输出内容
                            print(f"内容: {content}")
                    else:
                        print("未找到文档内容")
                        
                    print()  # 空白行分隔
            else:
                print("未找到相关文档")
        else:
            print("响应中没有数据")
            
        return response
            
    except Exception as e:
        print(f"检索失败: {e}")
        return None


if __name__ == "__main__":
    # 测试检索
    test_queries = [
        "灭火器过期未更换"
    ]
    
    print("进行简单测试检索...")
    for query in test_queries:
        print(f"\n测试问题: {query}")
        retrieve_from_knowledge_base(query)
        print("=" * 50)