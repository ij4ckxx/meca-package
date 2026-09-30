<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:ex="http://exslt.org/dates-and-times" xmlns:ali="http://www.niso.org/schemas/ali/1.0/" exclude-result-prefixes="xs ex">
    <xsl:output method="xml" doctype-system="JATS-journalpublishing1-3.dtd" doctype-public="-//NLM//DTD JATS (Z39.96) Journal Publishing DTD v1.3 20210610//EN" indent="no" encoding="UTF-8"/>
    <xsl:template match="@* | node()">
        <xsl:copy>
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>
    <xsl:template match="article">
        <article xmlns:mml="http://www.w3.org/1998/Math/MathML" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" article-type="{@article-type}" dtd-version="1.3" xml:lang="en">
            <xsl:apply-templates/>
        </article>
    </xsl:template>
    <!-- renaming <a> tag as < ext-link -->
    <xsl:template match="a | uri">
        <ext-link>
             <xsl:apply-templates select="@*[not(name()='rel')][not(name()='previewlistener')][not(name()='aria-label')]"/>
            <xsl:apply-templates/>
        </ext-link>
    </xsl:template>
    <!-- re order permission befor abstract -->
    <!-- <xsl:tempolate match=> -->
    <!-- reorder name tag's element -->
    <xsl:template match="name[.!='']">
        <name>
            <xsl:apply-templates select="@*"/>
            <xsl:apply-templates select=".//surname"/>
            <xsl:apply-templates select=".//given-names"/>
            <xsl:apply-templates select=".//prefix"/>
            <xsl:apply-templates select=".//suffix"/>
        </name>
    </xsl:template>
    <!-- reordering counts tags elements -->
    <xsl:template match="counts">
        <counts>
            <xsl:apply-templates select="node()[name()!='fig-count' and name()!='table-count' and name()!='equation-count' and name()!='ref-count' and name()!='page-count' and name()!='word-count']"/>
            <xsl:apply-templates select="fig-count"/>
            <xsl:apply-templates select="table-count"/>
            <xsl:apply-templates select="equation-count"/>
            <xsl:apply-templates select="ref-count"/>
            <xsl:apply-templates select="page-count"/>
            <xsl:apply-templates select="word-count"/>
        </counts>
    </xsl:template>
    <!-- re-ordering funding-group, counts, custom-meta-group -->
    <xsl:template match="article-meta">
        <article-meta>
            <xsl:apply-templates select= "node()[name()!='funding-group' and name()!='counts'and name()!='custom-meta-group' and name()!='notes']"/>
            <xsl:apply-templates select="funding-group"/>
            <xsl:apply-templates select="counts"/>
            <xsl:apply-templates select="custom-meta-group"/>
        </article-meta>
        <xsl:if test="notes">
            <notes>
                <xsl:apply-templates select="notes"/>
            </notes>
        </xsl:if>
        <!-- <xsl:apply-templates select="//article-meta/notes" mode="notesMovement"/> -->
    </xsl:template>
    <xsl:template match="//article-meta/notes" mode="notesMovement">
        <notes>
            <xsl:apply-templates />
        </notes>
    </xsl:template>
    <!-- moving contrib-id tag to top of contrib tag -->
    <xsl:template match="contrib[not(@data-track='del')]">
        <contrib>
            <xsl:if test="./xref[@ref-type='equal']">
				<xsl:attribute name="equal-contrib">yes</xsl:attribute>
			</xsl:if>
            <xsl:apply-templates select="@*|node()[name()='contrib-id']"/>
            <xsl:apply-templates select="node()[name()!='contrib-id']"/>
        </contrib>
    </xsl:template>
    <!-- add sec tag and @title to supplementary-material tag -->
    <xsl:template match="back[./supplementary-material]">
        <back>
            <xsl:apply-templates select="node()[name()!='supplementary-material']"/>
            <sec>
                <title>Supplementary material</title>
                <xsl:apply-templates select="supplementary-material"/>
            </sec>
        </back>
    </xsl:template>
    <!--change ali-license to ali:license_ref -->
    <xsl:template match="ali-license">
        <ali:license_ref>
            <xsl:apply-templates/>
        </ali:license_ref>
    </xsl:template>
    <!-- renaming named-content tag to institution and replaceing content-type attribute's value  -->
    <xsl:template match="aff/named-content">
        <xsl:choose>
            <xsl:when test="./@content-type='dept'">
                <institution content-type="department">
                    <xsl:apply-templates/>
                </institution>
            </xsl:when>
            <xsl:when test="./@content-type='institution'">
                <institution>
                    <xsl:apply-templates/>
                </institution>
            </xsl:when>
            <xsl:when test="./@content-type='city'">
                <addr-line content-type="city">
                    <xsl:apply-templates/>
                </addr-line>
            </xsl:when>
            <xsl:when test="./@content-type='state'">
                <addr-line content-type="state">
                    <xsl:apply-templates/>
                </addr-line>
            </xsl:when>
            <xsl:when test="./@content-type='country'">
                <country>
                    <xsl:apply-templates/>
                </country>
            </xsl:when>
            <xsl:otherwise>
                <addr-line>
                    <xsl:apply-templates/>
                </addr-line>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <!-- moving aff tag out of contrib-group -->
    <!-- <xsl:template match="contrib-group">
        <contrib-group>
            <xsl:apply-templates select="node()[name()!='aff']"/>
        </contrib-group>
        <xsl:apply-templates select="aff"/>
    </xsl:template> -->
    <!-- wrapping institution-id tag inside institution-wrap tag   -->
    <xsl:template match="institution-id[not(parent::institution-wrap)]">
        <institution-wrap>
            <institution-id>
                <xsl:apply-templates select="@*"/>
                <xsl:apply-templates />
            </institution-id>
        </institution-wrap>
    </xsl:template>
    <!-- replacing department to instituion tag and adding content-type attribevalue as department -->
    <xsl:template match="aff/department">
        <institution content-type="department">
            <xsl:apply-templates/>
        </institution>
    </xsl:template>
    <!-- adding attribute to email tag -->
    <xsl:template match="author-notes/corresp/email">
        <email xlink:href="{.}" xlink:type="simple">
            <xsl:apply-templates/>
        </email>
    </xsl:template>
    <xsl:template match="notes[@data-type]">
        <notes>
            <xsl:attribute name="notes-type">
                <xsl:value-of select="@data-type"/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </notes>
    </xsl:template>
    <xsl:template match="s">
        <xsl:element name="strike">
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>
    <!-- Handle graphic tag -->
    <xsl:template match="graphic">
        <xsl:copy>
            <xsl:copy-of select="@*[not(starts-with(name(), 'data-'))]"/>
        </xsl:copy>
    </xsl:template>
    <!-- changing attribute name -->
    <xsl:template match="@data-id">
        <xsl:attribute name="id">
            <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    <xsl:template match="@data-fn-type">
        <xsl:attribute name="fn-type">
            <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    <xsl:template match="ext-link/@data-href|a/@href">
        <xsl:attribute name="xlink:href">
            <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    <xsl:template match="ext-link/@data-type">
        <xsl:attribute name="ext-link-type">
            <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    <!-- Match only ext-link with data-href beginning with 'mailto:' -->
    <xsl:template match="ext-link[starts-with(@data-href, 'mailto:')]">
        <email xlink:href="{.}" xlink:type="simple">
            <xsl:apply-templates/>
        </email>
    </xsl:template>
    <xsl:template match="abstract/title[@data-level='2'][not(@data-class='jrnlDeleted')]|trans-abstract/title[@data-level='2'][not(@data-class='jrnlDeleted')]">
        <title data-level="1">
            <xsl:apply-templates select="@*[not(name() = 'data-level')] | node()"/>
        </title>
    </xsl:template>
    <xsl:template match="comment[@data-class='RefGenre']">
        <xsl:choose>
            <xsl:when test="parent::element-citation[@publication-type='software']">
                <version>
                    <xsl:attribute name="designator">
                        <xsl:apply-templates/>
                    </xsl:attribute>
                    <xsl:apply-templates/>
                </version>
            </xsl:when>
            <xsl:otherwise>
                <source>
                    <xsl:apply-templates/>
                </source>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <xsl:template match="span[@data-class='RefSoftSource']|span[@data-class='RefDataSourceTitle']">
        <source>
            <xsl:apply-templates/>
        </source>
    </xsl:template>
    <xsl:template match="span[@data-spl-style='jrnlSTIXGeneral_Italic']">
        <italic>
            <xsl:apply-templates/>
        </italic>
    </xsl:template>
    <xsl:template match="comment[@data-class='RefLAD']">
        <date-in-citation>
            <xsl:choose>
                <xsl:when test="preceding-sibling::span[@data-class='RefAccesedDay'] or preceding-sibling::comment[@data-class='RefAccesedDay'] and preceding-sibling::comment[@data-class='RefAccesedMonth'] or preceding-sibling::span[@data-class='RefAccesedMonth'] | following-sibling::span[@data-class='RefAccesedDay'] or following-sibling::comment[@data-class='RefAccesedDay'] and following-sibling::comment[@data-class='RefAccesedMonth'] or following-sibling::span[@data-class='RefAccesedMonth']">
                    <xsl:apply-templates select="preceding-sibling::span[@data-class='RefAccesedDay']/node()|preceding-sibling::comment[@data-class='RefAccesedDay']/node()|following-sibling::span[@data-class='RefAccesedDay']/node()|following-sibling::comment[@data-class='RefAccesedDay']/node()"/>
                    <xsl:text>-</xsl:text>
                    <xsl:apply-templates select="preceding-sibling::span[@data-class='RefAccesedMonth']/node()|preceding-sibling::comment[@data-class='RefAccesedMonth']/node()|following-sibling::span[@data-class='RefAccesedMonth']/node()|following-sibling::comment[@data-class='RefAccesedMonth']/node()"/>
                    <xsl:text>-</xsl:text>
                    <xsl:apply-templates/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:apply-templates/>
                </xsl:otherwise>
            </xsl:choose>
        </date-in-citation>
    </xsl:template>
    <xsl:template match="comment[@data-class='RefPrePrintLink']">
        <ext-link ext-link-type="uri">
            <xsl:attribute name="xlink:href">
                <xsl:value-of select="."/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </ext-link>
    </xsl:template>
    <!-- Handling span elements -->
    <xsl:template match="span[@data-class='RefStatus']">
        <comment>
            <xsl:apply-templates/>
        </comment>
    </xsl:template>
    <xsl:template match="span[@data-class='RefAnnote']">
        <comment>
            <xsl:apply-templates/>
        </comment>
    </xsl:template>
    <xsl:template match="span[@data-class='jrnlAniRef']">
        <xref ref-type="video">
            <xsl:attribute name ="rid">
                <xsl:value-of select="normalize-space(@data-citation-string)"/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </xref>
    </xsl:template>
    <xsl:template match="span[@data-class='jrnlPubIdType']">
        <pubtype>
            <xsl:apply-templates/>
        </pubtype>
    </xsl:template>
    <xsl:template match="span[@data-class='RefConference']">
        <conf-name>
            <xsl:apply-templates/>
        </conf-name>
    </xsl:template>
    <xsl:template match="span[@data-class='jrnlDataTitle']">
        <data-title>
            <xsl:apply-templates/>
        </data-title>
    </xsl:template>
    <xsl:template match="span[@data-class='partLabel']">
        <bold>
            <xsl:apply-templates/>
        </bold>
    </xsl:template>
    <xsl:template match="span[@data-class='label']">
        <label>
            <xsl:apply-templates/>
        </label>
    </xsl:template>
    <xsl:template match="body/child::*[1][not(self::title)]">
        <title/>
         <xsl:copy>
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>
    <xsl:template match="span[@data-class='jrnlPi']">
        <xsl:text disable-output-escaping="yes">&lt;?</xsl:text>
        <xsl:value-of select="@data-target"/>
        <xsl:text disable-output-escaping="yes"> </xsl:text>
        <xsl:value-of select="@data-instruction"/>
        <xsl:text disable-output-escaping="yes">?&gt;</xsl:text>
    </xsl:template>
    <xsl:template match="ref//year[starts-with(.,'n.d')]">
        <comment>
            <xsl:apply-templates/>
        </comment>
    </xsl:template>
    <xsl:template match="funding-group//award-group[not(@data-track='del')]">
        <award-group>
            <xsl:if test="@data-id">
                <xsl:attribute name="id">
                    <xsl:value-of select="@data-id"/>
                </xsl:attribute>
            </xsl:if>
            <xsl:apply-templates/>
        </award-group>
    </xsl:template>
    <xsl:template match="named-content[contains(@content-type, 'jrnlSmallCaps')][not(@data-track='del')]">
        <sc>
            <xsl:apply-templates/>
        </sc>
    </xsl:template>
    <xsl:template match="named-content[contains(@content-type, 'jrnlColor')][not(@data-track='del')]">
        <named-content>
            <xsl:attribute name="content-type">
                <xsl:value-of select="@data-text-color"/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </named-content>
    </xsl:template>
    <xsl:template match="a//named-content">
        <xsl:apply-templates/>
    </xsl:template>
    <!-- renaming valign value as midddle if its center(not allowed)-->
    <xsl:template match="//td/@valign[.='center']">
        <xsl:attribute name="valign">
            <xsl:text>middle</xsl:text>
        </xsl:attribute>
    </xsl:template>
    <xsl:template match="//td/@data-table-background-color|//th/@data-table-background-color|//tr/@data-table-background-color">
        <xsl:attribute name="data-table-background-color">
            <xsl:text>background:</xsl:text>
            <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
     <xsl:template match="//td/@data-text-color|//th/@data-text-color|//tr/@data-text-color">
        <xsl:attribute name="data-table-background-color">
            <xsl:text>color: </xsl:text>
            <xsl:value-of select="."/>
        </xsl:attribute>
    </xsl:template>
    <!-- multiple meta-value not allowed.remove meta-value and replace its text in single meta value -->
    <xsl:template match="custom-meta[count(meta-value)>1]/meta-value">
        <meta-value>
            <xsl:value-of select="."/>
            <xsl:for-each select="following-sibling::meta-value">
                <xsl:text>; </xsl:text>
                <xsl:value-of select="."/>
            </xsl:for-each>
        </meta-value>
    </xsl:template>
    <xsl:template match="custom-meta[count(meta-value)>1]/meta-value[position()>1]"/>
    <!-- Unwrap the Attributes and Elements -->
    <xsl:template match= "meta-value[.='']">
        <meta-value>
            <xsl:text>not available</xsl:text>
        </meta-value>
    </xsl:template>
    <!-- Adding comment tag for untagged content -->
    <xsl:template match= "element-citation/named-content/text()">
        <comment>
            <xsl:value-of select="."/>
        </comment>
    </xsl:template>
    <!-- If fn tag contanins H1, it should be lable tag -->
    <xsl:template match= "fn/h1">
        <label>
            <xsl:value-of select="."/>
        </label>
    </xsl:template>
    <!-- Adding tablewrap for boxed-text table -->
    <xsl:template match= "boxed-text/table">
        <table-wrap>
            <table>
                <xsl:apply-templates/>
            </table>
        </table-wrap>
    </xsl:template>
    <!-- related-article-type attribute adding -->
    <xsl:template match= "related-article">
        <related-article ext-link-type="doi">
			<xsl:attribute name="related-article-type">
				<xsl:choose>
					<xsl:when test="@related-article-type">
					    <xsl:value-of select="@related-article-type"/>
					</xsl:when>
					<xsl:otherwise>
						<xsl:text>other</xsl:text>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>		
			<xsl:attribute name="xlink:href">
				<xsl:choose>
					<xsl:when test="./pub-id[@pub-id-type='doi']">
						<xsl:value-of select="./pub-id[@pub-id-type='doi']"/>
					</xsl:when>
					<xsl:otherwise>
						<xsl:value-of select="substring-after(substring-after(./@xlink:href, '//'), '/')"/>
					</xsl:otherwise>
				</xsl:choose>
			</xsl:attribute>
			<xsl:if test="./volume[.!='']"><xsl:attribute name="vol"><xsl:value-of select="./volume"/></xsl:attribute></xsl:if>
			<xsl:if test="./fpage">
				<xsl:attribute name="page"><xsl:value-of select="./fpage"/><xsl:if test="./lpage">–<xsl:value-of select="./lpage"/></xsl:if></xsl:attribute>
			</xsl:if>
			<!-- <xsl:if test="./year[.!='']"><xsl:attribute name="year"><xsl:value-of select="./year"/></xsl:attribute></xsl:if> -->
			<xsl:if test="./elocation-id[.!='']"><xsl:attribute name="elocation-id"><xsl:value-of select="./elocation-id"/></xsl:attribute></xsl:if>
		</related-article>
    </xsl:template>
    <!-- Changing element citation to mixed citation-->
  <xsl:template match="element-citation">
        <mixed-citation>
            <xsl:attribute name="publication-type">
                 <xsl:value-of select="@publication-type"/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </mixed-citation>
    </xsl:template>
    <!-- correcting pub-date-->
    <xsl:template match= "pub-date">
        <pub-date>
            <xsl:attribute name="pub-type">
                <xsl:value-of select="@pub-type"/>
            </xsl:attribute>
            <day>
                <xsl:value-of select="day"/>
            </day>
            <month>
                <xsl:value-of select="month"/>
            </month>
            <year>
                <xsl:value-of select="year"/>
            </year>
        </pub-date>
    </xsl:template>
    <!-- Adding sec to the boxed-text element -->
    <xsl:template match="//boxed-text[not(@data-track='del')]">
        <boxed-text>
            <xsl:apply-templates select="@*"/>
            <xsl:if test="./label">
                <label>
                    <xsl:value-of select="label"/>
                </label>
            </xsl:if>
            <xsl:choose>
                <xsl:when test="count(./caption)=0 or ./caption[.='']"/>
                <xsl:otherwise>
                    <caption>
                        <title>
                            <!-- <xsl:apply-templates select="./caption/title/@*"/> -->
                            <xsl:apply-templates select="./caption/p/node()|./caption/title/node()"/>
                        </title>
                    </caption>
                </xsl:otherwise>
            </xsl:choose>
            <xsl:choose>
                <xsl:when test="node()[not(self::caption)][(self::title)]">
                    <xsl:for-each select="node()[not(self::caption)][(self::title)]">
                        <sec>
                            <title>
                                <!-- <xsl:apply-templates select="./title/@*"/> -->
                                <xsl:apply-templates/>
                            </title>
                            <xsl:call-template name="group">
                                <xsl:with-param name="node-set" select="following-sibling::*" />
                            </xsl:call-template>
                        </sec>
                    </xsl:for-each>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:apply-templates select="node()[not(self::caption)][not(self::label)]"/>
                </xsl:otherwise>
            </xsl:choose>
        </boxed-text>
    </xsl:template>
    <xsl:template name="group">
        <xsl:param name="node-set" />
        <xsl:if test="$node-set[1][self::p or self::list or self::fn-group]">
            <xsl:apply-templates select="$node-set[1]" />
            <xsl:call-template name="group">
                <xsl:with-param name="node-set" select="$node-set[position() &gt; 1]" />
            </xsl:call-template>
        </xsl:if>
    </xsl:template>
    <xsl:template match="def-list">
        <def-list>
            <xsl:apply-templates select="@*"/>
            <xsl:apply-templates select="node()[.!='.']"/>
        </def-list>
    </xsl:template>
    <xsl:template match="contrib[not(@data-track='del')][collab]">
        <contrib>
            <xsl:apply-templates select="@*"/>
            <xsl:variable name="id" select="xref[starts-with(@rid,'group-author')]/@rid"/>
            <collab>
                <xsl:apply-templates select="collab/node()"/>
                <xsl:apply-templates select="//contrib-group[@data-id=$id]" mode="collab"/>
            </collab>
            <xsl:apply-templates select="node()[name()!='collab']"/>
        </contrib>
    </xsl:template>
    <xsl:template match="//contrib-group[starts-with(@data-id,'group-author')]" mode="collab">
        <contrib-group>
            <xsl:apply-templates/>
        </contrib-group>
    </xsl:template>
    <!-- Match named-content elements with an italic ancestor and containing &ensp; -->
        <xsl:template match="named-content[
            ancestor::italic
            and contains(., '&#x2002;')
        ]">
        <!-- unwrap: apply-templates to children, but skip named-content element -->
        <xsl:apply-templates select="node()" />
    </xsl:template>
    <!-- arranging funding-group -->
    <xsl:template match="funding-group">
        <funding-group>
            <xsl:apply-templates select="award-group" />
            <xsl:apply-templates select="funding-statement" />
            <xsl:apply-templates select="open-access" />
            <xsl:apply-templates select="node()[name()!= 'award-group' and name()!= 'funding-statement' and name()!='open-access']"/>
        </funding-group>
    </xsl:template>

    <xsl:template match="abstract[@data-abstract-type='video']">
        <abstract abstract-type='video'>
            <p><xsl:apply-templates/></p>
        </abstract>
    </xsl:template>

    <xsl:template match="abstract[@data-abstract-type='graphical']">
        <abstract abstract-type='graphical'>
            <xsl:apply-templates/>
        </abstract>
    </xsl:template>

    <xsl:template match="license[@xlink:href]/@xlink:href">
        <xsl:attribute name="xlink:href">
            <xsl:choose>
                <xsl:when test="//license-p//ext-link/@data-href">
                    <xsl:value-of select="//license-p//ext-link/@data-href"/>
                </xsl:when>
                <xsl:when test="//license-p//ext-link/@xlink:href">
                    <xsl:value-of select="//license-p//ext-link/@xlink:href"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="."/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:attribute>
    </xsl:template>
    <xsl:template match="//td/p|//th/p">
		<xsl:choose>
			<xsl:when test="count(../p)&gt;1">
				<xsl:for-each select=".">
					<xsl:choose>
						<xsl:when test="preceding-sibling::p[1]">
							<break/><xsl:apply-templates />
						</xsl:when>
						<xsl:otherwise>
							<xsl:apply-templates />
						</xsl:otherwise>
					</xsl:choose>
				</xsl:for-each>
			</xsl:when>
			<xsl:otherwise>
				<xsl:apply-templates />
			</xsl:otherwise>
		</xsl:choose>
	</xsl:template>
    <xsl:template match="//*/@lang">
        <xsl:choose>
            <xsl:when test=".='null'"/>
            <xsl:otherwise>
                <xsl:attribute name="xml:lang">
                    <xsl:value-of select="." />
                </xsl:attribute>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xsl:template match="span[@data-spl-style='strike-through']">
        <strike>
            <xsl:apply-templates/>
        </strike>
    </xsl:template>

    <xsl:template match="table[@data-col-count]">
        <xsl:copy>
            <xsl:apply-templates select="@*[name() != 'data-col-count']"/>

            <colgroup>
                <xsl:call-template name="gen-cols">
                    <xsl:with-param name="n" select="number(@data-col-count)"/>
                </xsl:call-template>
            </colgroup>

            <xsl:apply-templates select="node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:template name="gen-cols">
        <xsl:param name="n" select="0"/>
        <xsl:if test="$n &gt; 0">
            <col align="left" span="1"/>
            <xsl:call-template name="gen-cols">
                <xsl:with-param name="n" select="$n - 1"/>
            </xsl:call-template>
        </xsl:if>
    </xsl:template>

    <!-- Unwrap the Attributes and Elements -->
    <xsl:template match="
    meta-value/reason|
    fpage/*|
    x|
    xref[./xref]|
    source/*|
    named-content[starts-with(@content-type,'ins')][not(parent::aff)]|
    named-content[contains(@content-type, 'sty ')][not(contains(@content-type, 'jrnlSmallCaps'))][not(contains(@content-type, 'jrnlColor'))]|
    named-content[@content-type='sty']|
    named-content[@content-type='indent']|
    named-content[@content-type='jrnlPatterns']|
    named-content[contains(@content-type, 'action')]|
    named-content[contains(@content-type, 'styrm')]|
    named-content[@content-type='styrm cts-2']|
    named-content[contains(@content-type, 'jrnlUncitedRef')][not(@data-track='del')]|scp|
    named-content[@content-type='nonBreakingSpace'][not(@data-track='del')]|
    named-content[.=' ']|
    volume/named-content/bold|
    volume/bold|
    issue/bold|
    volume/named-content|
    label/named-content|
    named-content[@content-type='forceJustify']|
    named-content[@content-type='forceColBrk']|
    named-content[contains(@content-type, 'Query')]|
    name/named-content|
    ext-link/break|
    title/break|
    bold/break|
    p/span[@data-class='label']|
    xref/ext-link|
    pub-id/a|
    date/data-latest|
    edition/italic|
    conf-name/italic|
    fig/fn|
    span|
    named-content[@content-type='dept']/italic|
    named-content[@content-type='sequence']">
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="//*[not(@data-class='jrnlDeleted') and not(@data-tract='del' and not(contains(@data-class,'del')))]
	[count(child::node())>0]
    [count(child::node()[not(parent::td)])>0]
	[count(*[starts-with(@data-class,'del')]|
    *[@data-class='jrnlDeleted']|
    *[@data-track='del']|
    *[@data-class='jrnlQueryRef']|
    *[@data-class='hidden']|
    *[@data-track='del'])=(count(child::node()))]|
    article-title[@content-type='del']|
    named-content[@content-type='del']|
    named-content[contains(@content-type, 'del ')]"/>
    <xsl:template match="*[@data-class='del']|
    *[@data-class='hidden'][@hidden-track='track']|
    *[contains(@data-track, 'del')]|
    *[@data-class='jrnlDelete']|
    *[@data-class='jrnlDeleted']|
    span[@data-class='forceJustify']|
    @old-class[.='']|
    bold[named-content[.='']][.='']|
    caption[.='']|
    xref/@id|
    //italic/@id|
    //bold/@id|
    td[@align='minus']/@align|
    a/@jsname|
    a/@jscontroller|
    a/@jsaction|
    custom-meta/meta-value/@specific-path|
    @pwa2-uuid|
    @pwa-fake-editor|
    xref[@ref-type='graph'][.='']|
    @bis_skin_checked|
    @spellcheck|
    xref[starts-with(@rid,'group-author')]|
    contrib[@contrib-type='author non-byline']|
    //contrib-group[starts-with(@data-id,'group-author')]"/>
    <!-- Removing Unwanted Attributes and Elements -->
    <xsl:template match="//*[not(name()='contrib' or name()='related-object')][@data-id]/@id|
    //article-meta/fpage[preceding-sibling::history]|
    //article-meta/lpage[preceding-sibling::history]|
    pub-date[.='']|
    fn/text()|
    uri/break|
    pub-id/@retain |
    name/@compared|
    supplementary-material/@fig-type|
    supplementary-material/text()|
    p/break|
    media/text()|
    media/@data-href|
    media/@data-type|
    p/@data-level|
    article-title/@data-level|
    mml:math/@colorcode|
    license/@*[.='']|
    table-wrap-foot[not(text())][.='']|
    article-meta/sec|
    contrib/text()|
    permissions//license[.='']|
    fn[not(p[normalize-space() != ''])]|
    def-item/@data-id|
    @section|
    @node-xpath|
    @prev-xpath|
    @next-xpath|
    @contenteditable|
    @class|
    @nodetype|
    @listnode|
    @width|
    @border|
    @cellspacing|
    @cellpadding|
    @height|
    @node-insert-xpath|
    @node-parent-node|
    @node-prev-xpath|
    @node-next-xpath|
    @node-insertafter-xpath|
    @node-insertbefore-xpath|
    @node-parent-insert-xpath|
    @node-parent-insertafter-xpath|
    @node-parent-insertbefore-xpath|
    @italic|
    @sdnum|
    @add-data-inserted|
    @fontsize|
    @bgcolor|
    @leftmargin|
    @link-array|
    @link-style|
    @textindent|
    @nowrap|
    @direct-node|
    @link-|
    @colorcode|
    @textdecoration|
    @new-id|
    @seqid|
    @headweightage|@wfd-id|p[@align]/@align|
    @retain-title-data|
    @data-group|
    @data-tex|
	disp-formula/@src|
	inline-formula/@src|
    def-item/@alphabetical-order|
    def-item/@fn-type|
    def/@remove-last-node-suffix|
    def/@set-last-node-suffix|
    ack/@fn-type|
    ref/@data-doi|
    ref/@sortby|
    ref/@first-author|
    ref/@sort-author|
    corresp/@fn-type|
    fn/@wt-ignore-input|
    xref/@data-type|
    boxed-text/@insert-citation|
    ref/@data-pmid|
    p/@listchar|
    p/@list-style-type|
    article-meta/files|
    p/@old-class|
    meta-value/@holdtype|
    permissions/@data-type|
    funding-statement/@fn-type|
    xref/@insert-at|
    sc/@fntsize|
    title/@id|
    supplementary-material/@data-type|
    custom-meta/@fn-type|
   custom-meta/@data-type|
   custom-meta/@ejp-file-name|
   custom-meta/@file-path|
   custom-meta/@type|
   given-names/@initial|
   ref/@text-indent|
   td/@text-indent|
   fn/@class-name|
   title/@fn-type|
   p/@fn-type|
   meta-name/@fn-type|
   subj-group/@data-p-template|
   license/@free-to-read|
   custom-meta/@processed-type|
   meta-value/@data-type|
   td/@dir|
   disp-quote/@data-type|
   p/@data-table-background-color|
   table-wrap/@data-type|
   fn/@data-type|
   boxed-text/@data-type|
   td/@sdval|
   title/@data-type|
   article-id[@pub-id-type='nlm-ta']|
   article-id[@pub-id-type='paw-acronomy']|
   article-meta[fpage[.='']]/elocation-id|
   ref/@list-style-type|
   ref/@listchar|
   fn/@list-style-type|
   fn/@listchar|
   abstract[not(@data-abstract-type='graphical')]/fig|
   kwd-group/boxed-text|
   ext-link/span[not(text())]|
   def-list/title[preceding-sibling::def-item]|
   article-meta/notes|
   article-meta/article-version|
   contrib/@id|
   conf-date/@event-start-day|
   conf-date/@event-start-year|
   conf-date/@event-start-month|
   conf-date/@event-end-day|
   conf-date/@event-end-year|
   conf-date/@event-end-month|
   //named-content[.='']|
   ref/@sort-year|
   contrib-group[contrib[@contrib-type='copyediting']]|
   issue[.='']|
   @_msttexthash|
   @_msthash"/>
    <xsl:template match="pub-date/@iso-8601-date|
    date/@iso-8601-date|
    paymentmethod|
    chaser-info|
    input-parameters|
    workflow|
    production-notes|
    gwmw|
    rc-c2d-number|
    icepaste|
    font|
    p/p|
    sup/sup|
    sc[.='']|
    custom-meta[@specific-use='track-changes']|
    license[.='']|
    //xref/@id|
    //role/@rid|
    //given-names[.='']|
    @id[.='']|
    //article-id[@pub-id-type='revised_manuscript_doi']|
    media/@data-abstract-type|
    @insert-before|
    //author-notes/text()[.=',']|
    //ref//span[@data-class='es-webpage-collect main']|
    custom-meta/@journal-prefrences-type"/>
    <!-- Retaining required self closed elements -->
    <xsl:template match="//*[.=''][count(*)=0]
    [not(name()='publisher-name')]
    [not(name()='journal-id')]
    [not(name()='issue')]
    [not(name()='counts')]
    [not(name()='abstract')]
    [not(name()='back')]
    [not(name()='word-count')]
    [not(name()='ref-count')]
    [not(name()='equation-count')]
    [not(name()='table-count')]
    [not(name()='page-count')]
    [not(name()='fig-count')]
    [not(name()='disp-formula')]
    [not(name()='inline-formula')]
    [not(name()='supplementary-material')]
    [not(name()='etal')]
    [not(name()='count')]
    [not(name()='uri')]
    [not(name()='ext-link')]
    [not(ancestor::td)]
    [not(ancestor::tr)]
    [not(ancestor::title)]
    [not(name()='inline-graphic')]
    [not(name()='related-article' and not(parent::*[name()]='article-meta'))]
    [not(name()='graphic')]
    [not(name()='col')]
    [not(name()='colgroup')]
    [not(name()='th')]
    [not(name()='td')]
    [not(name()='td/p')]
    [not(name()='institution')]
    [not(name()='self-uri')]
    [not(name()='self-url')]
    [not(name()='media')]
    [not(name()='xref' and not(parent::*[name()]='contrib'))]
    [not(ancestor::*[name()='mml:math'])]
    [not(ancestor::*[name()='math'])]
    [not(name()='inline-supplementary-material')]
    [not(name()='ali:free_to_read')]
    [not(name()='anchor')]
    [not(name()='related-object')]"/>
    <!-- Retaining required attributes which starts with "data-" -->
    <xsl:template match="@*[starts-with(name(), 'link-')][not(name()='link-type')]|
    @*[starts-with(name(), 'data-')]
    [not(name()='data-translate')]
    [not(name()='data-mathml')]
    [not(name()='data-abstract-type')]
    [not(name()='data-tex')]
    [not(name()='data-pmid')][not(name()='data-asterisk')]
    [not(name()='data-doi')]
    [not(name()='data-level')]
    [not(name()='data-href')]
    [not(name()='data-pdf-href')]
    [not(name()='data-id')]
    [not(name()='data-valign')]
    [not(name()='data-align')]
    [not(name()='data-group-type')]
    [not(name()='data-group')]
    [not(name()='data-table-background-color')]
    [not(name()='data-type')] [not(name()='data-p-template')]|
    td/@rowspan[.='1']|
    td/@colspan[.='1']|@*[starts-with(name(), 'tmp-')]|
    div|
    td/@valid|
    video-abstract-url|
    @readability|
    @huiyi-exclude-el"/>
    <!--abstract[not(@data-abstract-type='graphical abstract')]/title[@data-level='1']| -->
    <!-- Unwrap duplicated sub node -->
    <xsl:template match="italic//italic|
    title/bold|
    bold//bold|
    sup//sup|
    article-title/article-title|
    sub//sub|
    thead//td/p/bold|
    it|caption/title/journal-title|
    caption/p/journal-title|
    meta-value/named-content|
    corresp/fn|
    corresp/name|
    corresp/name/prefix|
    corresp/name/given-names|
    corresp/name/surname|
    corresp/name/degrees|
    corresp/fn/p|
    corresp/collab|
    fn/p/named-content[not(contains(@content-type, 'del '))][not(@content-type='del')]|
    meta-value/user-name|
    history/related-object|
    etal//italic|
    etal//bold|
    meta-value//question|
    meta-value//answer">
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="fn[not(@data-track='del')]//def-list[not(@data-track='del')]|
    fn[not(@data-track='del')]//def-list[not(@data-track='del')]/def-item[not(@data-track='del')]|
    fn[not(@data-track='del')]//def-list[not(@data-track='del')]/def-item[not(@data-track='del')]/def[not(@data-track='del')]|
    fn[not(@data-track='del')]//def-list[not(@data-track='del')]/def-item[not(@data-track='del')]/def[not(@data-track='del')]/p|
    fn[not(@data-track='del')]//def-list/def-item[not(@data-track='del')]/term[not(@data-track='del')]">
        <xsl:apply-templates/>
    </xsl:template>
    <!-- To remove the unwanted tags and values for the refLAD -->
    <xsl:template match="span[@data-class='RefAccesedDay']|span[@data-class='RefAccesedMonth']|comment[@data-class='RefAccesedDay']|comment[@data-class='RefAccesedMonth']|x[preceding-sibling::span[@data-class='RefAccesedDay']][1][following-sibling::span[@data-class='RefAccesedMonth']]|x[preceding-sibling::comment[@data-class='RefAccesedDay']][1][following-sibling::comment[@data-class='RefAccesedMonth']]|x[preceding-sibling::span[@data-class='RefAccesedMonth']][1]|x[preceding-sibling::comment[@data-class='RefAccesedMonth']][1]|//x[preceding-sibling::comment[@data-class='RefLAD']][1][following-sibling::span[@data-class='RefAccesedMonth'][1]]"/>
    <!-- <xsl:template name="replace-attrib">
		<xsl:param name="attrib"/>
		<xsl:param name="find"/>
		<xsl:param name="replace"/>
		<xsl:choose>
			<xsl:when test="$attrib = '' or not($find)">
				<xsl:value-of select="$attrib"/>
			</xsl:when>
			<xsl:when test="contains($attrib, $find)">
            	<xsl:value-of select="$replace"/>
                <xsl:value-of select="substring-after($attrib, $find)"/>
			
                </xsl:when>
		</xsl:choose>
	</xsl:template> -->
</xsl:stylesheet>