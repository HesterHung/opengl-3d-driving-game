#version 120

varying vec3 FragPos;
varying vec3 Normal;
varying vec2 TexCoord;

void main()
{
    FragPos = vec3(gl_ModelViewMatrix * gl_Vertex);
    Normal = normalize(gl_NormalMatrix * gl_Normal);
    TexCoord = gl_MultiTexCoord0.xy;
    gl_FrontColor = gl_Color;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
