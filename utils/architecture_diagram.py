"""
Architecture Diagram Generator using Mingrammer Diagrams
=========================================================

Tự động sinh AWS architecture diagrams từ project description với focus vào 
containerized architecture (ECS/Fargate).

Features:
- Tự động extract components từ project description bằng LLM
- Ưu tiên AWS ECS/Fargate cho modern containerized applications
- Hỗ trợ 90+ AWS service icons từ diagrams library
- Intelligent icon selection với fuzzy matching
- Tự động tạo connections giữa components

Future Enhancements:
- AI-generated custom icons cho unsupported services (using DALL-E/Stable Diffusion)
- Interactive diagram editing
- Cost estimation based on architecture

Author: AI Assistant
Date: 2025-10-07
Last Updated: 2025-10-07
"""

import os
import json
import tempfile
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from utils.logger import get_logger
from config import Config

logger = get_logger(__name__)


@dataclass
class Component:
    """System component với type và connections"""
    name: str
    component_type: str  # backend, frontend, database, mobile, integration, infrastructure
    description: str = ""
    icon_provider: str = "aws"  # aws, gcp, azure, k8s, etc.
    icon_name: str = "compute"  # EC2, Lambda, Database, etc.


@dataclass
class Connection:
    """Connection giữa 2 components"""
    source: str
    target: str
    label: str = ""


class ArchitectureDiagramGenerator:
    """
    Generator cho system architecture diagrams sử dụng Mingrammer Diagrams
    """

    # Component type mapping to Diagrams icons
    # Prioritize ECS/Fargate for containerized services
    ICON_MAPPING = {
        # Container Services (ECS First!)
        "ecs_service": ("aws.compute", "ECS"),
        "ecs_container": ("aws.compute", "ElasticContainerServiceContainer"),
        "ecs_task": ("aws.compute", "ElasticContainerServiceService"),
        "fargate": ("aws.compute", "Fargate"),
        "ecr": ("aws.compute", "ECR"),
        "eks": ("aws.compute", "EKS"),
        
        # Backend Services
        "backend_api": ("aws.compute", "ECS"),  # Default to ECS
        "backend_service": ("aws.compute", "ECS"),  # Default to ECS
        "microservice": ("aws.compute", "ECS"),
        "rest_api": ("aws.compute", "ECS"),
        "api_server": ("aws.compute", "ECS"),
        "lambda": ("aws.compute", "Lambda"),
        "ec2": ("aws.compute", "EC2"),
        "batch": ("aws.compute", "Batch"),

        # Frontend
        "web_frontend": ("aws.network", "CloudFront"),
        "web_app": ("aws.storage", "S3"),
        "spa": ("aws.storage", "S3"),
        "mobile_app": ("aws.general", "MobileClient"),
        "mobile_client": ("aws.general", "MobileClient"),

        # Database
        "sql_database": ("aws.database", "RDS"),
        "rds": ("aws.database", "RDS"),
        "mysql": ("aws.database", "RDSMysqlInstance"),
        "postgresql": ("aws.database", "RDSPostgresqlInstance"),
        "nosql_database": ("aws.database", "Dynamodb"),
        "dynamodb": ("aws.database", "Dynamodb"),
        "mongodb": ("aws.database", "DocumentDB"),
        "cache": ("aws.database", "ElastiCache"),
        "redis": ("aws.database", "ElasticacheForRedis"),
        "memcached": ("aws.database", "ElasticacheForMemcached"),
        "aurora": ("aws.database", "Aurora"),

        # API & Integration
        "api_gateway": ("aws.network", "APIGateway"),
        "apigw": ("aws.network", "APIGateway"),
        "message_queue": ("aws.integration", "SQS"),
        "sqs": ("aws.integration", "SQS"),
        "sns": ("aws.integration", "SNS"),
        "eventbridge": ("aws.integration", "Eventbridge"),
        "step_functions": ("aws.integration", "StepFunctions"),
        "mq": ("aws.integration", "MQ"),

        # Load Balancers
        "load_balancer": ("aws.network", "ELB"),
        "alb": ("aws.network", "ALB"),
        "nlb": ("aws.network", "NLB"),
        "elb": ("aws.network", "ELB"),

        # Network & CDN
        "cdn": ("aws.network", "CloudFront"),
        "cloudfront": ("aws.network", "CloudFront"),
        "route53": ("aws.network", "Route53"),
        "vpc": ("aws.network", "VPC"),
        "vpn": ("aws.network", "VpnGateway"),

        # Storage
        "storage": ("aws.storage", "S3"),
        "s3": ("aws.storage", "S3"),
        "efs": ("aws.storage", "EFS"),
        "fsx": ("aws.storage", "FSx"),

        # Security
        "cognito": ("aws.security", "Cognito"),
        "iam": ("aws.security", "IAM"),
        "secrets_manager": ("aws.security", "SecretsManager"),
        "waf": ("aws.security", "WAF"),

        # Monitoring
        "cloudwatch": ("aws.management", "Cloudwatch"),
        "xray": ("aws.devtools", "XRay"),

        # CI/CD
        "codepipeline": ("aws.devtools", "Codepipeline"),
        "codebuild": ("aws.devtools", "Codebuild"),
        "codedeploy": ("aws.devtools", "Codedeploy"),

        # Third Party & Generic
        "third_party": ("aws.general", "User"),
        "external_service": ("aws.general", "InternetGateway"),
        "client": ("aws.general", "User"),
        "user": ("aws.general", "User"),
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize diagram generator

        Args:
            api_key: OpenAI API key (defaults to Config)
            model: LLM model to use
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model
        self.llm = ChatOpenAI(
            api_key=self.api_key,
            model=self.model,
            temperature=0.3
        )
        logger.info(f"ArchitectureDiagramGenerator initialized with model: {model}")

    def extract_components(self, project_description: str) -> Tuple[List[Component], List[Connection]]:
        """
        Extract system components và connections từ project description

        Args:
            project_description: Detailed project description text

        Returns:
            Tuple of (components, connections)
        """
        logger.info("Extracting components from project description")

        # Craft extraction prompt with ECS focus
        extraction_prompt = f"""
Analyze the following project description and extract AWS architecture components for a MODERN CONTAINERIZED system.

PROJECT DESCRIPTION:
{project_description}

Extract system architecture components in JSON format.

**IMPORTANT GUIDELINES:**
1. **Prioritize AWS ECS/Fargate** for backend services and microservices (containerized architecture)
2. Use ECS unless there's a specific reason to use Lambda (serverless) or EC2 (traditional VMs)
3. Focus on HIGH-LEVEL components only (5-10 main components)
4. Keep it simple and clear for technical proposals

Return ONLY valid JSON in this exact format:
{{
  "components": [
    {{
      "name": "Component Name",
      "type": "component_type",
      "description": "Brief description"
    }}
  ],
  "connections": [
    {{
      "source": "Component A",
      "target": "Component B",
      "label": "HTTP/gRPC/async/etc"
    }}
  ]
}}

**Component Type Reference:**

Container Services (PREFERRED for modern apps):
- ecs_service: ECS Service (Docker containers on Fargate/EC2)
- fargate: AWS Fargate (serverless containers)
- ecs_container: Individual container in ECS
- ecr: Container image registry
- eks: Kubernetes clusters (if K8s is mentioned)

Compute:
- backend_api: REST API service → Default to ECS
- backend_service: Backend microservice → Default to ECS
- microservice: Microservice → Default to ECS
- lambda: Serverless functions (for event-driven, not main APIs)
- ec2: Virtual machines (only if specifically mentioned)

Frontend:
- web_frontend: Web UI (CloudFront + S3)
- spa: Single Page Application (S3)
- mobile_app: Mobile application

Databases:
- rds/mysql/postgresql: Relational databases
- dynamodb: NoSQL key-value store
- mongodb: Document database (DocumentDB)
- redis/cache: In-memory cache (ElastiCache)
- aurora: High-performance RDS

Integration:
- api_gateway: API Gateway for REST/WebSocket APIs
- alb: Application Load Balancer (for ECS services)
- sqs: Message queue (async processing)
- sns: Pub/Sub notifications
- eventbridge: Event bus

Storage & CDN:
- s3: Object storage
- cloudfront: CDN
- efs: Shared file system

Security:
- cognito: User authentication
- secrets_manager: Secrets storage
- waf: Web Application Firewall

Monitoring:
- cloudwatch: Logging and monitoring
- xray: Distributed tracing

Third Party:
- third_party: External APIs (Stripe, SendGrid, etc.)
- client: End users

**Architecture Pattern Example:**
For a typical web application:
- Users → CloudFront → ALB → ECS Services → RDS/DynamoDB
- ECS Services → ElastiCache (Redis)
- API Gateway → ECS Services (if API-first)

Extract components now.
"""

        try:
            messages = [
                SystemMessage(content="You are a system architect expert. Extract architecture components accurately in JSON format."),
                HumanMessage(content=extraction_prompt)
            ]

            response = self.llm.invoke(messages)
            response_text = response.content

            logger.debug(f"LLM response: {response_text[:200]}...")

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                # Try to extract JSON directly
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                else:
                    raise ValueError("No valid JSON found in LLM response")

            data = json.loads(json_text)

            # Parse components
            components = []
            for comp_data in data.get('components', []):
                comp_type = comp_data.get('type', 'backend_service')
                icon_module, icon_name = self._get_icon_for_type(comp_type)

                component = Component(
                    name=comp_data.get('name', 'Unknown'),
                    component_type=comp_type,
                    description=comp_data.get('description', ''),
                    icon_provider=icon_module,
                    icon_name=icon_name
                )
                components.append(component)

            # Parse connections
            connections = []
            for conn_data in data.get('connections', []):
                connection = Connection(
                    source=conn_data.get('source', ''),
                    target=conn_data.get('target', ''),
                    label=conn_data.get('label', '')
                )
                connections.append(connection)

            logger.info(f"Extracted {len(components)} components and {len(connections)} connections")
            return components, connections

        except Exception as e:
            logger.error(f"Error extracting components: {str(e)}")
            # Return empty lists on error
            return [], []

    def _get_icon_for_type(self, component_type: str) -> Tuple[str, str]:
        """
        Get Diagrams icon module và name cho component type
        
        If component type not found, try to infer from context or use generic icon

        Returns:
            Tuple of (icon_module, icon_name)
        """
        # Try exact match first
        if component_type in self.ICON_MAPPING:
            return self.ICON_MAPPING[component_type]
        
        # Try fuzzy matching for common patterns
        comp_lower = component_type.lower()
        
        # Container-related
        if any(keyword in comp_lower for keyword in ['container', 'docker', 'ecs', 'fargate']):
            return ("aws.compute", "ECS")
        
        # API-related
        if any(keyword in comp_lower for keyword in ['api', 'rest', 'graphql', 'service']):
            return ("aws.compute", "ECS")
        
        # Database-related
        if any(keyword in comp_lower for keyword in ['db', 'database', 'sql']):
            return ("aws.database", "RDS")
        
        # Queue/messaging
        if any(keyword in comp_lower for keyword in ['queue', 'message', 'kafka', 'mq']):
            return ("aws.integration", "SQS")
        
        # Storage
        if any(keyword in comp_lower for keyword in ['storage', 'file', 'object']):
            return ("aws.storage", "S3")
        
        # Default fallback: Use generic User icon for unknown types
        logger.warning(f"Unknown component type '{component_type}', using generic icon")
        return ("aws.general", "User")

    def generate_diagram_code(self, components: List[Component], connections: List[Connection],
                               diagram_name: str = "System Architecture") -> str:
        """
        Generate Python Diagrams code từ components và connections

        Args:
            components: List of Component objects
            connections: List of Connection objects
            diagram_name: Diagram title

        Returns:
            Python code string
        """
        logger.info(f"Generating diagram code for {len(components)} components")

        # Create mapping from component names to variable names
        # This ensures connections reference the correct variables
        name_to_var = {}
        for comp in components:
            var_name = self._sanitize_var_name(comp.name)
            # Handle duplicate variable names by adding suffix
            original_var = var_name
            counter = 1
            while var_name in name_to_var.values():
                var_name = f"{original_var}_{counter}"
                counter += 1
            name_to_var[comp.name] = var_name

        # Generate imports
        imports = ["from diagrams import Diagram, Cluster, Edge"]
        icon_imports = set()

        for comp in components:
            icon_import = f"from diagrams.{comp.icon_provider} import {comp.icon_name}"
            icon_imports.add(icon_import)

        imports.extend(sorted(icon_imports))

        # Generate code
        code_lines = imports + ["", ""]
        code_lines.append(f'with Diagram("{diagram_name}", show=False, direction="LR", filename="system_architecture"):')

        # Create component variables
        for comp in components:
            var_name = name_to_var[comp.name]
            code_lines.append(f'    {var_name} = {comp.icon_name}("{comp.name}")')

        # Add spacing
        code_lines.append("")

        # Create connections with proper variable lookup
        for conn in connections:
            # Find matching component names (case-insensitive and fuzzy)
            source_var = self._find_component_var(conn.source, name_to_var)
            target_var = self._find_component_var(conn.target, name_to_var)

            if source_var and target_var:
                if conn.label:
                    code_lines.append(f'    {source_var} >> Edge(label="{conn.label}") >> {target_var}')
                else:
                    code_lines.append(f'    {source_var} >> {target_var}')
            else:
                logger.warning(f"Skipping connection: {conn.source} -> {conn.target} (component not found)")

        return "\n".join(code_lines)
    
    def _find_component_var(self, name: str, name_to_var: Dict[str, str]) -> Optional[str]:
        """
        Find variable name for a component, with fuzzy matching
        
        Args:
            name: Component name from connection
            name_to_var: Mapping of component names to variable names
            
        Returns:
            Variable name if found, None otherwise
        """
        # Try exact match first
        if name in name_to_var:
            return name_to_var[name]
        
        # Try case-insensitive match
        name_lower = name.lower()
        for comp_name, var_name in name_to_var.items():
            if comp_name.lower() == name_lower:
                return var_name
        
        # Try fuzzy match (contains or is contained)
        for comp_name, var_name in name_to_var.items():
            if name_lower in comp_name.lower() or comp_name.lower() in name_lower:
                logger.debug(f"Fuzzy matched '{name}' to component '{comp_name}'")
                return var_name
        
        logger.error(f"Component '{name}' not found in diagram. Available: {list(name_to_var.keys())}")
        return None

    def _sanitize_var_name(self, name: str) -> str:
        """
        Sanitize component name to valid Python variable name
        
        Args:
            name: Component name (may contain spaces, special chars)
            
        Returns:
            Valid Python variable name (lowercase, underscores)
        """
        # Remove special characters and spaces, replace with underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Remove consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        
        # Ensure it starts with a letter (not digit or underscore)
        if sanitized and sanitized[0].isdigit():
            sanitized = 'comp_' + sanitized
        
        # Fallback if empty after sanitization
        if not sanitized:
            sanitized = 'component'
            
        return sanitized.lower()

    def generate_diagram(self, project_description: str, output_dir: str = "./architecture_diagrams") -> Optional[str]:
        """
        Complete workflow: extract components → generate code → create diagram

        Args:
            project_description: Project description text
            output_dir: Directory to save diagram PNG

        Returns:
            Path to generated PNG file, or None if failed
        """
        logger.info("Starting diagram generation workflow")

        try:
            # Convert output_dir to absolute path to avoid issues when changing directories
            output_dir = os.path.abspath(output_dir)
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Step 1: Extract components
            components, connections = self.extract_components(project_description)

            if not components:
                logger.warning("No components extracted from project description")
                return None

            # Step 2: Generate diagram code
            diagram_code = self.generate_diagram_code(components, connections)

            logger.debug(f"Generated diagram code:\n{diagram_code}")

            # Step 3: Execute diagram code in temporary environment
            with tempfile.TemporaryDirectory() as temp_dir:
                # Change to temp directory to generate diagram there
                original_dir = os.getcwd()
                os.chdir(temp_dir)

                try:
                    # Execute diagram code
                    exec(diagram_code)

                    # Find generated PNG file
                    png_file = os.path.join(temp_dir, "system_architecture.png")

                    if os.path.exists(png_file):
                        # Move to output directory
                        import shutil
                        final_path = os.path.join(output_dir, "system_architecture.png")
                        shutil.move(png_file, final_path)

                        logger.info(f"Diagram generated successfully: {final_path}")
                        return final_path
                    else:
                        logger.error("PNG file not generated")
                        return None

                finally:
                    os.chdir(original_dir)

        except Exception as e:
            logger.exception(f"Error generating diagram: {str(e)}")
            return None

    def generate_ai_icon(self, component_name: str, component_type: str, style: str = "aws") -> Optional[str]:
        """
        Generate custom icon using DALL-E 3 (GPT-4o) image generation
        
        Creates high-quality, semantic-aware icons for system components using OpenAI's
        DALL-E 3 API. Icons are generated in the specified style and saved to a local directory.
        
        Args:
            component_name: Name of the component (e.g., "User Authentication Service")
            component_type: Type of component (e.g., "backend_api", "database", "cache")
            style: Icon style - "aws" (default), "flat", "3d", or "minimalist"
            
        Returns:
            Path to generated icon PNG file, or None if generation failed
            
        Example usage:
            icon_path = generator.generate_ai_icon(
                "Custom ML Service", 
                "machine_learning",
                style="aws"
            )
        """
        try:
            from openai import OpenAI
            from PIL import Image
            import requests
            from io import BytesIO
            
            logger.info(f"Generating AI icon for '{component_name}' ({component_type}, style={style})")
            
            # Create custom_icons directory if not exists
            custom_icons_dir = os.path.join(Config.ARCHITECTURE_DIAGRAMS_DIR, "custom_icons")
            os.makedirs(custom_icons_dir, exist_ok=True)
            
            # Initialize OpenAI client
            client = OpenAI(api_key=self.api_key)
            
            # Craft semantic-aware prompt based on component type and style
            style_descriptions = {
                "aws": "AWS-style minimalist flat icon with clean lines, blue/orange color scheme, simple geometric shapes, professional tech aesthetic",
                "flat": "Modern flat design icon with vibrant colors, simple shapes, minimal shadows, Material Design inspired",
                "3d": "Isometric 3D icon with depth, soft shadows, modern tech aesthetic, clean and professional",
                "minimalist": "Ultra-minimalist line art icon, monochrome, essential shapes only, clean and simple"
            }
            
            style_desc = style_descriptions.get(style, style_descriptions["aws"])
            
            # Component type to semantic description mapping
            semantic_hints = {
                "backend_api": "server, API endpoints, REST/GraphQL service",
                "backend_service": "microservice, server process, backend logic",
                "database": "data storage, database server, data tables",
                "cache": "high-speed memory, Redis/Memcached, fast data access",
                "message_queue": "message broker, queue system, async communication",
                "api_gateway": "API gateway, traffic routing, request management",
                "load_balancer": "traffic distribution, load balancing, server routing",
                "storage": "object storage, file system, data persistence",
                "frontend": "web interface, user interface, browser application",
                "mobile_app": "mobile device, smartphone, mobile interface",
                "lambda": "serverless function, cloud function, event-driven compute",
                "ecs_service": "container service, Docker, containerized application",
                "fargate": "serverless container, AWS Fargate, managed containers",
            }
            
            semantic_hint = semantic_hints.get(component_type, "cloud service, system component")
            
            prompt = f"""Create a {style_desc} representing '{component_name}' - a {semantic_hint}.

Requirements:
- Icon should be SQUARE (1:1 aspect ratio)
- Clear, recognizable symbol that represents {component_type}
- Professional, suitable for technical architecture diagrams
- Simple enough to be recognizable at small sizes (64x64px)
- Semantic meaning should be immediately clear
- No text or labels in the icon
- Clean background (white or transparent-ready)
- Focus on the core concept: {component_name}"""

            logger.debug(f"DALL-E prompt: {prompt}")
            
            # Generate image using DALL-E 3
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",  # DALL-E 3 supports 1024x1024, 1792x1024, 1024x1792
                quality="standard",  # or "hd" for higher quality
                n=1,
            )
            
            image_url = response.data[0].url
            logger.debug(f"Generated image URL: {image_url}")
            
            # Download image
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()
            
            # Open and process image
            img = Image.open(BytesIO(img_response.content))
            
            # Resize to standard icon size (256x256 for high quality, can scale down)
            icon_size = (256, 256)
            img = img.resize(icon_size, Image.Resampling.LANCZOS)
            
            # Convert to RGBA if not already
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Generate filename
            safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', component_name.lower())
            filename = f"{safe_name}_{component_type}_{style}.png"
            output_path = os.path.join(custom_icons_dir, filename)
            
            # Save image
            img.save(output_path, 'PNG', optimize=True)
            
            logger.info(f"AI icon generated successfully: {output_path}")
            return output_path
            
        except ImportError as e:
            logger.error(f"Missing required library for icon generation: {str(e)}")
            logger.info("Install required packages: pip install openai pillow requests")
            return None
            
        except Exception as e:
            logger.exception(f"Error generating AI icon: {str(e)}")
            return None

    def get_diagram_info(self, components: List[Component], connections: List[Connection]) -> Dict[str, Any]:
        """
        Get summary information about extracted architecture

        Returns:
            Dict with component counts và statistics
        """
        component_types = {}
        for comp in components:
            comp_type = comp.component_type
            component_types[comp_type] = component_types.get(comp_type, 0) + 1

        return {
            'total_components': len(components),
            'total_connections': len(connections),
            'component_types': component_types,
            'components': [{'name': c.name, 'type': c.component_type, 'description': c.description} for c in components],
            'connections': [{'source': c.source, 'target': c.target, 'label': c.label} for c in connections]
        }
