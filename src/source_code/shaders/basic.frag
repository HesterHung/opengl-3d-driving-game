#version 120

varying vec3 FragPos;
varying vec3 Normal;
varying vec2 TexCoord;

uniform bool useTexture;
uniform sampler2D texture1;
uniform bool useLighting;
uniform bool lightEnabled[8];

void main()
{
    if (!useLighting) {
        if (useTexture) {
            gl_FragColor = texture2D(texture1, TexCoord);
        } else {
            gl_FragColor = gl_Color;
        }
        return;
    }

    vec3 norm = normalize(Normal);
    vec3 viewDir = normalize(-FragPos);
    
    vec3 totalAmbient = gl_FrontLightModelProduct.sceneColor.rgb + 
                        gl_FrontMaterial.ambient.rgb * gl_LightModel.ambient.rgb;
                        
    vec3 totalDiffuse = vec3(0.0);
    vec3 totalSpecular = vec3(0.0);
    
    for(int i = 0; i < 8; i++) {
        if (!lightEnabled[i]) continue;
        
        vec3 lightDir;
        float attenuation = 1.0;
        
        if (gl_LightSource[i].position.w == 0.0) {
            // Directional Light
            lightDir = normalize(gl_LightSource[i].position.xyz);
        } else {
            // Point or Spot Light
            vec3 lightVec = gl_LightSource[i].position.xyz - FragPos;
            float distance = length(lightVec);
            lightDir = normalize(lightVec);
            
            attenuation = 1.0 / (gl_LightSource[i].constantAttenuation + 
                                 gl_LightSource[i].linearAttenuation * distance + 
                                 gl_LightSource[i].quadraticAttenuation * distance * distance);
        }
        
        // Spot Light
        if (gl_LightSource[i].spotCutoff <= 90.0) {
            float theta = dot(lightDir, normalize(-gl_LightSource[i].spotDirection));
            if (theta < cos(radians(gl_LightSource[i].spotCutoff))) {
                attenuation = 0.0;
            } else {
                attenuation *= pow(theta, gl_LightSource[i].spotExponent);
            }
        }
        
        vec3 ambient = gl_FrontMaterial.ambient.rgb * gl_LightSource[i].ambient.rgb;
        
        float diff = max(dot(norm, lightDir), 0.0);
        vec3 diffuse = gl_FrontMaterial.diffuse.rgb * gl_LightSource[i].diffuse.rgb * diff;
        
        // Blinn-Phong Specular
        vec3 halfwayDir = normalize(lightDir + viewDir);
        float spec = pow(max(dot(norm, halfwayDir), 0.0), gl_FrontMaterial.shininess);
        vec3 specular = gl_FrontMaterial.specular.rgb * gl_LightSource[i].specular.rgb * spec;
        
        totalAmbient += ambient * attenuation;
        totalDiffuse += diffuse * attenuation;
        totalSpecular += specular * attenuation;
    }
    
    vec3 result = totalAmbient + totalDiffuse + totalSpecular + gl_FrontMaterial.emission.rgb;
    
    vec4 texColor = vec4(1.0);
    if (useTexture) {
        texColor = texture2D(texture1, TexCoord);
    }
    
    gl_FragColor = vec4(result, gl_FrontMaterial.diffuse.a) * texColor;
}
