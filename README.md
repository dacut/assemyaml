# Assemyaml
Assemble and merge multiple YAML sources into a single document.

The goal is to weakly couple YAML documents together for final assembly. For
example, a CloudFormation template for a three-tier architecture might contain
definitions for individual containers:

```yaml
Resources:
  ECSTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      ContainerDefinitions:
        - # Frontend container
          Image: !Ref ReactImage
          PortMappings:
            - ContainerPort: 8080
              HostPort: 80
              Protocol: tcp
        - # Backend container
          Image: !Ref FlaskImage
          PortMappings:
            - ContainerPort: 8080
              HostPort: 1080
              Protocol: tcp
        - # MongoDB container
          Image: !Ref MongoDBImage
          MountPoints:
            - ContainerPath: /opt/mongodb
              SourceVolume: mongodb
```

This works ok _if_ you're keeping the infrastructure, frontend, backend, and
database bits in the same repository. Or you could break everything into
separate CloudFormation stacks and hope you get all of the cross-dependencies
right.

Neither approach _felt_ right for a simple website being developed by a small
but plural number of developers. I wanted to keep the corresponding frontend,
backend, and database source for code and infrastructure together
and assemble them into a master template (with a few other support pieces in
an infrastructure repository).

The above would become three separate documents:

<table><tr><th>Infrastructure::cfn.yml</th><th>React::cfn.yml</th><th>Flask::cfn.yml</th><th>MongoDB::cfn.yml</th></tr>
<tr><td valign="top"><pre>Resources:
  ECSTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      ContainerDefinitions:
        !Transclude ContainerDefinitions</pre></td>
<td valign="top"><pre>!Assembly ContainerDefinitions:
  - # Frontend container
    Image: !Ref ReactImage
    PortMappings:
      - ContainerPort: 8080
        HostPort: 80
        Protocol: tcp</pre></td>
<td valign="top"><pre>!Assembly ContainerDefinitions:
  - # Backend container
    Image: !Ref FlaskImage
    PortMappings:
      - ContainerPort: 8080
        HostPort: 1080
        Protocol: tcp</pre></td>
<td valign="top"><pre>!Assembly ContainerDefinitions:
  - # MongoDB container
    Image: !Ref MongoDBImage
    MountPoints:
      - ContainerPath: /opt/mongodb
        SourceVolume: mongodb</pre></td></tr></table>

## Syntax

Assemyaml provides two local tags, `!Transclude` and `!Assembly`.

The `!Transclude` tag specifies a transclusion point -- where another document may specify
one or more YAML collections (sequence or mapping). It takes a string name used as a label
for the transclusion point. The transclusion is a mapping key; if the value is not null,
it is used as an assembly for that transclusion point.

The `!Assembly` tag specifies an assembly -- one or more YAML collections to be injected
into a corresponding transclusion point. It takes a string specifying the transclusion label.
If multiple documents provide the same assembly, the collection **must** be the same type;
you cannot mix sequences and mappings. If the assemblies are mappings, they **must**
have unique keys.

One document is designated the template. This document is written to the output, with all
`!Transclude` directives overwritten. The other documents are called resources.

## Simple examples

<table><tr><th>Template document</th><th>Resource 1</th><th>Resource 2</th><th>Result</th></tr>
<tr><td valign="top"><pre>Hello:
  !Transclude values:
    - Alpha
    - Bravo</pre></td>
<td valign="top"><pre>
!Transclude values:
  - Charlie
  - Delta</pre></td>
<td valign="top"><pre>
!Transclude values:
  - Echo
  - Foxtrot</pre></td>
<td valign="top"><pre>Hello:
  - Alpha
  - Bravo
  - Charlie
  - Delta
  - Echo
  - Foxtrot</pre></td>
</tr></table>
