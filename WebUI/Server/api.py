import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import Body
from WebUI.Server.chat.completion import completion
from WebUI.Server.utils import (FastAPI, MakeFastAPIOffline, BaseResponse, ListResponse)
from WebUI.configs.serverconfig import OPEN_CROSS_DOMAIN
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from WebUI.Server.chat.chat import chat
from WebUI.Server.embeddings_api import embed_texts_endpoint
from WebUI.Server.chat.openai_chat import openai_chat
from WebUI.Server.llm_api import (list_running_models, get_running_models, list_config_models,
                            change_llm_model, stop_llm_model,
                            get_model_config, save_chat_config, save_model_config, get_webui_configs, list_search_engines)
from WebUI.Server.utils import(get_prompt_template)
from typing import List, Literal
from __about__ import __version__

async def document():
    return RedirectResponse(url="/docs")

def create_app(run_mode: str = None):
    app = FastAPI(
        title="Langchain-Chatchat API Server",
        version=__version__
    )
    MakeFastAPIOffline(app)
    # Add CORS middleware to allow all origins
    # 在config.py中设置OPEN_DOMAIN=True，允许跨域
    # set OPEN_DOMAIN=True in config.py to allow cross-domain
    if OPEN_CROSS_DOMAIN:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    mount_app_routes(app, run_mode=run_mode)
    return app

def mount_app_routes(app: FastAPI, run_mode: str = None):
    app.get("/",
            response_model=BaseResponse,
            summary="swagger document")(document)

    # Tag: Chat
    app.post("/chat/fastchat",
             tags=["Chat"],
             summary="Conversing with a llm model.(through the FastChat API)",
             )(openai_chat)

    app.post("/chat/chat",
             tags=["Chat"],
             summary="Conversing with a llm model.(through the LLMChain)",
             )(chat)
    
    app.post("/llm_model/save_chat_config",
             tags=["Chat"],
             summary="Save chat configration information",
             )(save_chat_config)

    #app.post("/chat/search_engine_chat",
    #         tags=["Chat"],
    #         summary="与搜索引擎对话",
    #         )(search_engine_chat)

    #app.post("/chat/feedback",
    #         tags=["Chat"],
    #         summary="返回llm模型对话评分",
    #         )(chat_feedback)

    # 知识库相关接口
    #mount_knowledge_routes(app)

    # LLM Model interface
    app.post("/llm_model/list_running_models",
             tags=["LLM Model Management"],
             summary="List current running Model",
             )(list_running_models)
    
    app.post("/llm_model/get_running_models",
             tags=["LLM Model Management"],
             summary="Get current running Model",
             )(get_running_models)

    app.post("/llm_model/list_config_models",
             tags=["LLM Model Management"],
             summary="List Model configration information",
             )(list_config_models)

    app.post("/llm_model/get_model_config",
             tags=["LLM Model Management"],
             summary="Get Model configration information",
             )(get_model_config)
    
    app.post("/llm_model/save_model_config",
             tags=["LLM Model Management"],
             summary="Save Model configration information",
             )(save_model_config)

    app.post("/llm_model/stop",
             tags=["LLM Model Management"],
             summary="Stop LLM Model (Model Worker)",
             )(stop_llm_model)

    app.post("/llm_model/change",
             tags=["LLM Model Management"],
             summary="Switch to new LLM Model (Model Worker)",
             )(change_llm_model)

    # Server interface
    app.post("/server/get_webui_config",
             tags=["Server State"],
             summary="get webui config",
             )(get_webui_configs)
    #app.post("/server/configs",
    #         tags=["Server State"],
    #         summary="获取服务器原始配置信息",
    #         )(get_server_configs)

    #app.post("/server/list_search_engines",
    #         tags=["Server State"],
    #         summary="获取服务器支持的搜索引擎",
    #         )(list_search_engines)

    @app.post("/server/get_prompt_template",
             tags=["Server State"],
             summary="获取服务区配置的 prompt 模板")
    def get_server_prompt_template(
        type: Literal["llm_chat", "knowledge_base_chat", "search_engine_chat", "agent_chat"]=Body("llm_chat", description="模板类型，可选值：llm_chat，knowledge_base_chat，search_engine_chat，agent_chat"),
        name: str = Body("default", description="模板名称"),
    ) -> str:
        return get_prompt_template(type=type, name=name)

    # 其它接口
    app.post("/other/completion",
             tags=["Other"],
             summary="要求llm模型补全(通过LLMChain)",
             )(completion)

    app.post("/other/embed_texts",
            tags=["Other"],
            summary="将文本向量化，支持本地模型和在线模型",
            )(embed_texts_endpoint)