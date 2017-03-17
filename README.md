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

The above would become four separate documents maintained in separate repositories:

<table><tr><th>Infrastructure::cfn.yml</th><th>React::cfn.yml</th></tr>
<tr><td valign="top"><pre lang="yaml">Resources:
  ECSTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      ContainerDefinitions:
        !Transclude ContainerDefinitions
        </pre></td>
<td valign="top"><pre lang="yaml">!Assembly ContainerDefinitions:
  - # Frontend container
    Image: !Ref ReactImage
    PortMappings:
      - ContainerPort: 8080
        HostPort: 80
        Protocol: tcp</pre></td></tr><tr><th>Flask::cfn.yml</th><th>MongoDB::cfn.yml</th></tr>
<tr><td valign="top"><pre lang="yaml">!Assembly ContainerDefinitions:
  - # Backend container
    Image: !Ref FlaskImage
    PortMappings:
      - ContainerPort: 8080
        HostPort: 1080
        Protocol: tcp</pre></td>
<td valign="top"><pre lang="yaml">!Assembly ContainerDefinitions:
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

The mapping containing the `!Transclude` tag **must not** contain any other elements.

The `!Assembly` tag specifies an assembly -- one or more YAML collections to be injected
into a corresponding transclusion point. It takes a string specifying the transclusion label.
If multiple documents provide the same assembly, the collection **must** be the same type;
you cannot mix sequences and mappings. If the assemblies are mappings, they **must**
have unique keys.

One document is designated the template. This document is written to the output, with all
`!Transclude` mappings replaced by the assembled values. The other documents are called resources.

## Simple examples

<table><tr><th>Template document</th><th>Resource 1</th><th>Resource 2</th><th>Result</th></tr>
<tr><td valign="top"><pre lang="yaml">Hello:
  !Transclude values:
    - Alpha
    - Bravo</pre></td>
<td valign="top"><pre lang="yaml">
!Assembly values:
  - Charlie
  - Delta</pre></td>
<td valign="top"><pre lang="yaml">
!Assembly values:
  - Echo
  - Foxtrot</pre></td>
<td valign="top"><pre lang="yaml">Hello:
  - Alpha
  - Bravo
  - Charlie
  - Delta
  - Echo
  - Foxtrot</pre></td>
</tr></table>

<table><tr><th>Template document</th><th>Resource 1</th><th>Resource 2</th><th>Result</th></tr>
<tr><td valign="top"><pre lang="yaml">Hello:
  !Transclude values:
    Alpha: 1
    Bravo: 2</pre></td>
<td valign="top"><pre lang="yaml">
!Assembly values:
  Charlie: 3
  Delta: 4</pre></td>
<td valign="top"><pre lang="yaml">
!Assembly values:
  Echo: 5
  Foxtrot: 6</pre></td>
<td valign="top"><pre lang="yaml">Hello:
  Alpha: 1
  Bravo: 2
  Charlie: 3
  Delta: 4
  Echo: 5
  Foxtrot: 6</pre></td>
</tr></table>

## Global Tags

If you're using local tags `!Transclude` or `!Assembly` for another purpose (or if local tags
offend you), you may tell Assemyaml to use global tags instead:

<table><tr><th>Template document</th><th>Resource document</th></tr>
<tr><td valign="top"><pre lang="yaml">%TAG !assemyaml! tag:assemyaml.nz,2017:
---
Hello:
  !assemyaml!Transclude values:
  - Alpha
</pre></td>
<td valign="top"><pre lang="yaml">%TAG !assemyaml! tag:assemyaml.nz,2017:
---
!assemyaml!Assembly values:
  - Bravo
</pre></td></table>

## Command-line Usage

<code>assemyaml [options] <em>template-document</em> <em>resource-documents</em>...</code><br>
<code>assemyaml [options] --template <em>template-document</em> <em>resource-documents</em>...</code>

Options:
* <code>--no-local-tag</code> - Ignore <code>!Transclude</code> and <code>!Assembly</code>
  local tags and use global tags only.
* <code>--output <em>filename</em></code> - Write output to <em>filename</em> instead of stdout.

## CodePipeline/Lambda Usage

When used as a [Lambda invocation stage in CodePipeline](http://docs.aws.amazon.com/codepipeline/latest/userguide/actions-invoke-lambda-function.html), UserParameters is a JSON object with the following syntax:
<pre lang="json">{
    "TemplateDocument": "<em>input-artifact</em>::<em>filename</em>",
    "ResourceDocuments": ["<em>input-artifact</em>::<em>filename</em>", ...],
    "DefaultInputFilename": "<em>filename</em>",
    "OutputFilename": "<em>filename</em>",
    "LocalTag": true|false
}</pre>

All parameters are optional.

`TemplateDocument` specifies the input artifact and the filename within the artifact to use as the template document.

`ResourceDocuments` specifies the input artifacts and filename within each artifact to use as resource documents. Any input artifacts not referenced in either `TemplateDocuments` or `ResourceDocuments` are appended to `ResourceDocuments` as `artifact::DefaultInputFilename`.

The `DefaultInputFilename` key is used for an input artifact filename if an input artifact is not referenced in either `TemplateDocument` or `ResourceDocuments`. It defaults to `assemble.yml`.

`OutputFilename` specifies the filename to write in the output artifact. It defaults to `assemble.yml`.

`LocalTag` specifies whether the `!Transclude` and `!Assembly` local tags are allowed. It defaults to true.

If `TemplateDocument` or `ResourceDocument` is not specified, the following behavior applies:

<table><tr><th>Options specified</th><th>Input artifacts: `[A, B, C]`</th></tr>
<tr><td><pre lang="json">{
    "TemplateDocument": "B::f2",
    "ResourceDocuments": [ "A::f1", "C::f3" ]
}</pre></td><td><pre lang="json">{
    "TemplateDocument": "B::f2",
    "ResourceDocuments": [ "A::f1", "C::f3" ]
}</pre></td></tr>
<tr><td><pre lang="json">{
    "TemplateDocument": "B::f2"
}</pre></td><td><pre lang="json">{
    "TemplateDocument": "B::f2",
    "ResourceDocuments": [ "A::assemble.yml", "C::assemble.yml" ]
}</pre></td></tr>
<tr><td><pre lang="json">{
    "ResourceDocuments": [ "A::f1", "C::f3" ]
}</pre></td><td><pre lang="json">{
    "TemplateDocument": "B::assemble.yml",
    "ResourceDocuments": [ "A::f1", "C::f3" ]
}</pre></td></tr>
<tr><td><pre lang="json">{
    "ResourceDocuments": [ "C::f3" ]
}</pre></td><td><pre lang="json">{
    "TemplateDocument": "A::assemble.yml",
    "ResourceDocuments": [ "C::f3", "B::assemble.yml" ]
}</pre></td></tr>
<tr><td><pre lang="json"></pre></td>
<td><pre lang="json">{
    "TemplateDocument": "A::assemble.yml",
    "ResourceDocuments": [ "B::assemble.yml", "C::assemble.yml" ]
}</pre></td></table>
