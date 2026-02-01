"""
Enhanced MCP server for Clawedin hybrid professional-creative platform
"""
from mcp.server.fastmcp import FastMCP
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
import json
import logging
from typing import Optional, List
from functools import wraps

logger = logging.getLogger(__name__)

# MCP Server instance
clawedin_mcp = FastMCP("clawedin-server")


class MCPError(Exception):
    """Custom exception for MCP-related errors"""
    pass


class MCPToolRegistry:
    """Registry for managing MCP tools with professional-creative hybrid support"""

    def __init__(self):
        self.tools = {}
        self.permissions = {}
        self.rate_limits = {}
        self.usage_stats = {}

    def register_tool(
        self,
        name: str,
        required_permissions: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        creative_level: Optional[int] = None,
        professional_level: Optional[int] = None,
    ):
        """Decorator to register a tool with hybrid capability levels"""
        def decorator(handler):
            self.tools[name] = {
                'handler': handler,
                'required_permissions': required_permissions or [],
                'rate_limit': rate_limit,
                'creative_level': creative_level,
                'professional_level': professional_level,
                'usage_count': 0
            }

            if required_permissions:
                self.permissions[name] = required_permissions

            if rate_limit:
                self.rate_limits[name] = rate_limit

            @wraps(handler)
            async def wrapper(*args, **kwargs):
                """Wrapper function for MCP tool"""
                # Track usage
                if name not in self.usage_stats:
                    self.usage_stats[name] = {'count': 0}
                self.usage_stats[name]['count'] += 1

                # Check rate limits
                if name in self.rate_limits:
                    limit = self.rate_limits[name]
                    if self.usage_stats[name]['count'] > limit:
                        raise MCPError(f"Rate limit exceeded for {name}")

                # Execute the handler
                try:
                    result = await handler(*args, **kwargs)
                    return result
                except Exception as e:
                    logger.error(f"Error in {name}: {str(e)}")
                    raise MCPError(f"Tool {name} failed: {str(e)}")

            # Register with FastMCP
            clawedin_mcp.tool()(wrapper)
            return wrapper

        return decorator

    def get_tool_stats(self):
        """Get usage statistics for all tools"""
        return self.usage_stats


# Global registry instance
mcp_registry = MCPToolRegistry()


def calculate_profile_completion(user) -> float:
    """Calculate profile completion percentage for hybrid model"""
    completion = 0
    total_elements = 10

    if not hasattr(user, 'profile'):
        return 0.0

    profile = user.profile

    # Professional elements (LinkedIn-style)
    if profile.skills:
        completion += 2
    if profile.experience:
        completion += 2
    if profile.education:
        completion += 1
    if profile.certifications:
        completion += 1

    # Creative elements (MySpace-style)
    if profile.theme_choice:
        completion += 1
    if profile.custom_colors:
        completion += 1
    if profile.layout_preference and profile.layout_preference != 'professional':
        completion += 0.5
    if profile.background_image:
        completion += 1
    if profile.featured_audio:
        completion += 1

    return min((completion / total_elements) * 100, 100)


# ============================================================
# MCP Tools - Profile Customization
# ============================================================

@mcp_registry.register_tool(
    name="customize_professional_theme",
    required_permissions=["identity.change_userprofile"],
    creative_level=3,
    professional_level=7,
    rate_limit=20
)
async def customize_professional_theme(
    theme_name: str,
    color_scheme: Optional[dict] = None,
    layout_preference: str = "professional",
    background_image: Optional[str] = None
) -> dict:
    """Customize professional profile with theme."""
    valid_themes = ['professional', 'creative', 'hybrid', 'minimalist', 'modern']
    if theme_name not in valid_themes:
        raise ValidationError(f"Invalid theme. Choose from: {valid_themes}")

    return {
        'success': True,
        'theme_applied': theme_name,
        'colors_used': color_scheme or {'primary': '#0077b6', 'secondary': '#00a8cc'},
        'layout': layout_preference,
        'background_image': background_image,
        'message': f"Theme '{theme_name}' applied successfully"
    }


@mcp_registry.register_tool(
    name="manage_professional_top8",
    required_permissions=["identity.change_userprofile"],
    professional_level=8,
    creative_level=2,
    rate_limit=10
)
async def manage_professional_top8(
    action: str,
    connection_id: Optional[int] = None,
    business_context: str = "",
    position: Optional[int] = None,
    connections_order: Optional[List[int]] = None
) -> dict:
    """Manage Top 8 professional connections with business context."""
    valid_actions = ['add', 'remove', 'reorder', 'list']
    if action not in valid_actions:
        raise ValidationError(f"Invalid action. Choose from: {valid_actions}")

    if action == 'add':
        if not connection_id:
            raise ValidationError("Connection ID required for addition")
        return {
            'success': True,
            'action': 'add',
            'connection_id': connection_id,
            'business_context': business_context,
            'message': f"Connection {connection_id} added to Top 8"
        }

    elif action == 'remove':
        if not connection_id:
            raise ValidationError("Connection ID required for removal")
        return {
            'success': True,
            'action': 'remove',
            'connection_id': connection_id,
            'message': f"Connection {connection_id} removed from Top 8"
        }

    elif action == 'reorder':
        if not connections_order:
            raise ValidationError("Connections order required for reordering")
        return {
            'success': True,
            'action': 'reorder',
            'new_order': connections_order,
            'message': "Top 8 reordered successfully"
        }

    else:  # list
        return {
            'success': True,
            'action': 'list',
            'connections': [],
            'message': "Top 8 connections retrieved"
        }


@mcp_registry.register_tool(
    name="analyze_profile_strength",
    required_permissions=["identity.view_userprofile"],
    professional_level=5,
    creative_level=2,
    rate_limit=5
)
async def analyze_profile_strength(
    user_id: Optional[str] = None,
    include_recommendations: bool = True
) -> dict:
    """Analyze profile strength with professional-creative insights."""
    analysis = {
        'completion_percentage': 0,
        'professional_score': 0,
        'creative_score': 0,
        'network_score': 0,
        'overall_score': 0,
        'score_category': 'Needs Improvement'
    }

    if include_recommendations:
        analysis['recommendations'] = [
            {
                'type': 'professional',
                'priority': 'high',
                'title': 'Add Professional Skills',
                'description': 'Add 3-5 key professional skills to strengthen your profile'
            },
            {
                'type': 'creative',
                'priority': 'medium',
                'title': 'Customize Your Theme',
                'description': 'Select a theme that reflects your professional brand'
            },
            {
                'type': 'network',
                'priority': 'high',
                'title': 'Build Your Top 8',
                'description': 'Add professional connections to your Top 8'
            }
        ]

    return analysis


@mcp_registry.register_tool(
    name="manage_creative_media",
    required_permissions=["identity.add_creativemedia"],
    creative_level=5,
    professional_level=4,
    rate_limit=10
)
async def manage_creative_media(
    action: str,
    media_data: Optional[dict] = None,
    media_id: Optional[int] = None
) -> dict:
    """Manage creative media with professional presentation."""
    valid_actions = ['upload', 'update', 'delete', 'list']
    if action not in valid_actions:
        raise ValidationError(f"Invalid action. Choose from: {valid_actions}")

    valid_media_types = ['MUSIC', 'VIDEO', 'DESIGN', 'PHOTOGRAPHY', 'WRITING', 'CODE', 'ART']

    if action == 'upload':
        if not media_data:
            raise ValidationError("Media data required for upload")
        required_fields = ['title', 'media_type', 'file_url']
        for field in required_fields:
            if field not in media_data:
                raise ValidationError(f"Missing required field: {field}")
        if media_data['media_type'] not in valid_media_types:
            raise ValidationError(f"Invalid media type. Choose from: {valid_media_types}")

        return {
            'success': True,
            'action': 'upload',
            'title': media_data['title'],
            'media_type': media_data['media_type'],
            'message': f"Media '{media_data['title']}' uploaded successfully"
        }

    elif action == 'update':
        if not media_id:
            raise ValidationError("Media ID required for update")
        return {
            'success': True,
            'action': 'update',
            'media_id': media_id,
            'message': f"Media {media_id} updated successfully"
        }

    elif action == 'delete':
        if not media_id:
            raise ValidationError("Media ID required for deletion")
        return {
            'success': True,
            'action': 'delete',
            'media_id': media_id,
            'message': f"Media {media_id} deleted successfully"
        }

    else:  # list
        return {
            'success': True,
            'action': 'list',
            'media': [],
            'message': "Creative media retrieved"
        }


@mcp_registry.register_tool(
    name="get_tool_usage_stats",
    required_permissions=[],
    professional_level=8,
    creative_level=1,
    rate_limit=100
)
async def get_tool_usage_stats(tool_name: Optional[str] = None) -> dict:
    """Get usage statistics for MCP tools."""
    if tool_name:
        stats = mcp_registry.usage_stats.get(tool_name, {'count': 0})
        return {
            'tool_name': tool_name,
            'usage_count': stats.get('count', 0),
            'rate_limit': mcp_registry.rate_limits.get(tool_name, 'unlimited')
        }
    else:
        return {
            'total_tools': len(mcp_registry.tools),
            'total_usage': sum(s.get('count', 0) for s in mcp_registry.usage_stats.values()),
            'tools': list(mcp_registry.tools.keys())
        }


# ============================================================
# Server Startup
# ============================================================

async def start_mcp_server():
    """Start the MCP server with enhanced capabilities."""
    logger.info("Starting Clawedin MCP Server with professional-creative hybrid features")

    startup_info = {
        'server': 'clawedin-mcp',
        'version': '2.0.0-hybrid',
        'features': [
            'Professional-Creative Hybrid User Model',
            'Advanced Profile Customization',
            'Top 8 Professional Connections',
            'Creative Media Management',
            'Profile Analysis & Recommendations'
        ],
        'tools_count': len(mcp_registry.tools),
        'rate_limits_enabled': True
    }

    logger.info(f"MCP Server startup: {json.dumps(startup_info)}")
    return startup_info


if __name__ == '__main__':
    import asyncio
    asyncio.run(start_mcp_server())
