"""
OMA Streamlit Modules Package
Modules separated by each page
"""

# Import all page modules
from .welcome import render_welcome_page
from .project_env_info import render_project_env_page
from .app_analysis import render_app_analysis_page
from .app_reporting import render_app_reporting_page
from .discovery_report_review import render_discovery_report_review_page
from .postgresql_meta import render_postgresql_meta_page
from .log_viewer import render_running_logs_page
from .mapper_validation import render_mapper_validation_page
from .sample_transform import render_sample_transform_page
from .full_transform import render_full_transform_page
from .test_fix import render_test_fix_page
from .merge_transform import render_merge_transform_page
from .parameter_config import render_parameter_config_page
from .source_sqls import render_source_sqls_page
from .transform_report import render_transform_report_page
from .view_transform_report import render_view_transform_report_page
from .java_transform import render_java_transform_page

__all__ = [
    'render_welcome_page',
    'render_project_env_page', 
    'render_app_analysis_page',
    'render_app_reporting_page',
    'render_discovery_report_review_page',
    'render_postgresql_meta_page',
    'render_running_logs_page',
    'render_mapper_validation_page',
    'render_sample_transform_page',
    'render_full_transform_page',
    'render_test_fix_page',
    'render_merge_transform_page',
    'render_parameter_config_page',
    'render_source_sqls_page',
    'render_transform_report_page',
    'render_view_transform_report_page',
    'render_java_transform_page'
]
